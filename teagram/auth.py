import logging
import asyncio

from os import remove
from sys import exit

from configparser import ConfigParser, NoSectionError, NoOptionError

from qrcode.main import QRCode

from pyrogram import errors
from pyrogram.types import User

from pyrogram.raw.functions.account.get_password import GetPassword

from .web import WebCore
from .client import CustomClient

from . import __version__

logger = logging.getLogger(__name__)


def get_port():
    import socket

    for port in range(1024, 65535 + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))

                return port
            except OSError:
                continue


class Authorization:
    def __init__(
        self,
        test_mode: bool,
        no_qr: bool,
        no_web: bool,
        port: int,
    ):
        api_id, api_hash = self.get_api_tokens(not no_web)

        self.client = CustomClient(
            "../teagram_v2",
            api_id=api_id,
            api_hash=api_hash,
            device_model="Windows 10",
            app_version=__version__,
            test_mode=test_mode,
        )

        self.no_qr = no_qr
        self.no_web = no_web

        self.port = port

    def get_api_tokens(self, no_prompt: bool):
        self.config = ConfigParser()
        self.config.read("./config.ini")

        def api_prompt():
            self.config["api_tokens"] = {
                "api_id": input("Enter API ID: "),
                "api_hash": input("Enter API HASH: "),
            }

        try:
            if not self.config.get("api_tokens", "api_id") or not self.config.get(
                "api_tokens", "api_hash"
            ):
                if no_prompt:
                    return 0, "_"

                api_prompt()
        except (NoSectionError, NoOptionError):
            if no_prompt:
                return 0, "_"

            api_prompt()

        with open("./config.ini", "w") as file:
            self.config.write(file)

        try:
            api_id = self.config.get("api_tokens", "api_id")
            api_hash = self.config.get("api_tokens", "api_hash")
        except Exception:
            api_id, api_hash = 0, "_"

        return api_id, api_hash

    async def get_password(self):
        from getpass import getpass

        await self.client.invoke(GetPassword())

        while True:
            twofa = getpass("Enter 2FA password: ")
            try:
                return await self.client.check_password(twofa)
            except errors.PasswordHashInvalid:
                logger.error("Invalid password, retrying...")
            except errors.FloodWait as err:
                logger.error(f"FloodWait error; retry after {err.value} seconds")

    async def get_phone_code(self):
        while True:
            try:
                phone = input("Enter phone number: ")

                result = await self.client.send_code(phone)
                return phone, result.phone_code_hash
            except errors.PhoneNumberInvalid:
                logger.error("Invalid phone number, retrying...")
            except errors.PhoneNumberFlood as error:
                logger.error(f"Phone floodwait; retry after: {error.value} seconds")
            except errors.PhoneNumberBanned:
                logger.error("Phone number banned, retrying...")
            except errors.PhoneNumberOccupied:
                logger.error("Phone number already in use, retrying...")
            except errors.BadRequest:
                logger.error("Bad request, retrying...")

    async def enter_phone_code(self, phone, phone_code_hash, code=None):
        if not code:
            code = input("Enter confirmation code: ")
        try:
            return await self.client.sign_in(phone, phone_code_hash, code)
        except errors.SessionPasswordNeeded:
            await self.get_password()
            return await self.enter_phone_code(phone, phone_code_hash, code)

    async def generate_qrcode_from_url(self, url: str):
        qr = QRCode(error_correction=1)
        qr.clear()

        qr.add_data(url)

        qr.make()
        qr.print_ascii()

    async def authorize(self):
        if await self._is_authorized():
            return self.client

        if not self.no_web:
            return await self._web_authorize()
        elif not self.no_qr:
            return await self._qr_authorize()
        else:
            return await self._phone_authorize()

    async def _is_authorized(self):
        try:
            await self.client.connect()

            me = await self.client.get_me()
            return me is not None
        except errors.SessionRevoked:
            logger.error("Session revoked, deleting session file.")
            try:
                remove("teagram_v2.session")
            except PermissionError:
                logger.info(
                    "No permission to delete session file, please remove manually."
                )
            exit(64)
        except (errors.AuthKeyUnregistered, AttributeError):
            return False
        finally:
            try:
                await self.client.disconnect()
            except ConnectionError:
                pass

    async def _web_authorize(self):
        self.port = self.port or get_port()

        web = WebCore(port=self.port, test_mode=self.client.test_mode)

        client = await web.run()
        del web

        return client

    async def _qr_authorize(self):
        from pyrogram.qrlogin import QRLogin

        await self.client.connect()

        qr_login = QRLogin(self.client)
        await qr_login.recreate()

        user = None
        while not isinstance(user, User):
            try:
                logger.info("Scan the QR code below:")
                logger.info(
                    "Settings > Privacy and Security > Active Sessions > Scan QR Code"
                )
                await self.generate_qrcode_from_url(qr_login.url)

                user = await qr_login.wait(10)
            except errors.SessionPasswordNeeded:
                user = await self.get_password()
            except asyncio.TimeoutError:
                await qr_login.recreate()

        await self.client.disconnect()
        return self.client

    async def _phone_authorize(self):
        await self.client.connect()

        phone, phone_hash = await self.get_phone_code()

        await self.enter_phone_code(phone, phone_hash)
        await self.client.disconnect()

        return self.client
