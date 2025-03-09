import json
import asyncio
import logging

from pathlib import Path
from configparser import ConfigParser, NoSectionError, NoOptionError

from aiohttp import web, WSMsgType

from ..client import CustomClient

from pyrogram import errors
from pyrogram.types import User

from pyrogram.qrlogin import QRLogin
from pyrogram.raw.functions.account.get_password import GetPassword

from .. import __version__

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
PAGE_DIR = BASE_DIR / "page"


class WebsocketServer:
    def __init__(
        self,
        login_success: asyncio.Event = None,
        test_mode: bool = False,
        *args,
        **kwargs,
    ):
        self.login_success = login_success or asyncio.Event()
        self.connection = None
        self.test_mode = test_mode

        self.data = None
        self.client = None
        self.qr_login = None
        self.qr_wait = None

        self.app = web.Application()
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/ws", self.handler)
        self.app.router.add_static("/static", path=PAGE_DIR / "static", name="static")

        self._config_path = BASE_DIR.parent.parent / "config.ini"

        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config = self.load_config()

        super().__init__(*args, **kwargs)

    def load_config(self) -> ConfigParser:
        config = ConfigParser()
        if self._config_path.is_file():
            config.read(str(self._config_path))

        return config

    async def index(self, _) -> web.Response:
        return web.FileResponse(path=PAGE_DIR / "index.html")

    async def handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        if self.connection is not None:
            await ws.close(code=1008, message=b"Too many connections")
            return ws

        self.connection = ws

        try:
            api_id = self._config.get("api_tokens", "api_id")
            api_hash = self._config.get("api_tokens", "api_hash")
            if not api_id or not api_hash:
                await self.connection.send_json({"type": "enter_tokens"})
            else:
                self.client = CustomClient(
                    "../teagram_v2",
                    api_id=api_id,
                    api_hash=api_hash,
                    device_model="Windows 10",
                    app_version=__version__,
                    test_mode=self.test_mode,
                )

                await self.client.connect()
                await self.handle_qr_authorization()
        except (NoSectionError, NoOptionError):
            await self.connection.send_json({"type": "enter_tokens"})

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self.handle_message(msg.data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error("WebSocket error: %s", ws.exception())
        except Exception as exc:
            logger.exception("Error during message handling: %s", exc)
        finally:
            self.connection = None

        return ws

    async def handle_message(self, message: str):
        if self.connection is None:
            return

        message_data = json.loads(message)
        message_type = message_data.get("type")

        if message_type == "tokens":
            await self.handle_tokens(message_data)
        elif message_type == "phone_number":
            await self.handle_phone_number(message_data)
        elif message_type == "phone_code":
            await self.handle_phone_code(message_data)
        elif message_type == "cloud_auth":
            await self.handle_cloud_auth(message_data)
        elif message_type == "authorize_qr":
            await self.handle_qr_authorization()
        else:
            await self.connection.send_json(
                {"type": "error", "content": "Unknown message type"}
            )

    async def handle_tokens(self, message_data: dict):
        api_id = message_data.get("API_ID")
        api_hash = message_data.get("API_HASH")

        if not self._config.has_section("api_tokens"):
            self._config.add_section("api_tokens")

        self._config.set("api_tokens", "api_id", api_id)
        self._config.set("api_tokens", "api_hash", api_hash)

        with open(self._config_path, "w") as file:
            self._config.write(file)

        self.client = CustomClient(
            "../teagram_v2",
            api_id=api_id,
            api_hash=api_hash,
            device_model="Windows 10",
            app_version=__version__,
            test_mode=self.test_mode,
        )

        await self.client.connect()
        await self.handle_qr_authorization()

    async def handle_phone_number(self, message_data: dict):
        phone_number = message_data.get("phone_number")
        try:
            result = await self.client.send_code(phone_number)
            self.data = (phone_number, result.phone_code_hash)

            await self.connection.send_json(
                {"type": "message", "content": "Success! Sent code to Telegram..."}
            )
        except errors.PhoneNumberInvalid:
            await self.connection.send_json(
                {"type": "error", "content": "Invalid phone number, please try again."}
            )
        except errors.PhoneNumberFlood as error:
            await self.connection.send_json(
                {
                    "type": "error",
                    "content": f"Phone floodwait, retry after: {error.value}",
                }
            )
        except errors.PhoneNumberBanned:
            await self.connection.send_json(
                {
                    "type": "error",
                    "content": "Phone number banned, please try another number.",
                }
            )
        except errors.PhoneNumberOccupied:
            await self.connection.send_json(
                {"type": "error", "content": "Phone number is already in use."}
            )
        except errors.BadRequest:
            await self.connection.send_json(
                {"type": "error", "content": "Bad request, please try again."}
            )

    async def handle_phone_code(self, message_data: dict):
        if not self.data:
            await self.connection.send_json(
                {"type": "error", "content": "Missing phone data."}
            )
            return

        phone_number, phone_code_hash = self.data
        phone_code = message_data.get("phone_code")

        try:
            await self.client.sign_in(phone_number, phone_code_hash, phone_code)
            await self.stop()
        except errors.SessionPasswordNeeded:
            await self.connection.send_json(
                {
                    "type": "session_password_needed",
                    "content": "Password required for session.",
                }
            )

    async def handle_cloud_auth(self, message_data: dict):
        try:
            await self.client.invoke(GetPassword())
            await self.client.check_password(message_data.get("password"))

            await self.connection.send_json(
                {"type": "message", "content": "Cloud authentication successful."}
            )

            await self.stop()
        except errors.SessionPasswordNeeded:
            await self.connection.send_json(
                {
                    "type": "session_password_needed",
                    "content": "Password required for cloud authentication.",
                }
            )
        except Exception as e:
            logger.error("Cloud auth error: %s", e)
            await self.connection.send_json(
                {"type": "error", "content": "Cloud authentication failed."}
            )

    async def handle_qr_authorization(self):
        if not self.qr_login and not self.qr_wait:
            self.qr_login = QRLogin(self.client, [])
            await self.qr_login.recreate()

            self.qr_wait = asyncio.create_task(self.wait_qr_login())

    async def wait_qr_login(self):
        state = False
        last_url = self.qr_login.url

        await self.connection.send_json(
            {"type": "qr_login", "content": self.qr_login.url}
        )

        while not state:
            try:
                try:
                    state = await self.qr_login.wait(10)

                    if isinstance(state, User):
                        await self.stop()
                except asyncio.TimeoutError:
                    current_url = self.qr_login.url
                    while last_url == current_url:
                        await asyncio.sleep(0.5)

                        await self.qr_login.recreate()
                        current_url = self.qr_login.url

                    last_url = current_url
                    await self.connection.send_json(
                        {"type": "qr_login", "content": current_url}
                    )
            except errors.SessionPasswordNeeded:
                return await self.connection.send_json(
                    {
                        "type": "session_password_needed",
                        "content": "Password required for session.",
                    }
                )

    async def stop(self):
        try:
            await self.connection.close(code=1000)
            await self.client.disconnect()

            self.qr_wait.cancel()

            await self.runner.shutdown()
            self.login_success.set()
        except Exception as e:
            pass

    async def start_server(self, port: int):
        self.runner = web.AppRunner(self.app)

        await self.runner.setup()
        server = web.TCPSite(self.runner, None, port)

        await server.start()
