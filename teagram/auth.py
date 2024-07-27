import asyncio

from configparser import ConfigParser, NoSectionError, NoOptionError
from pyrogram import Client, errors

from pyrogram.raw.functions.account.get_password import GetPassword
from pyrogram.raw.functions.auth.export_login_token import ExportLoginToken

from pyrogram.raw.types.auth.login_token import LoginToken
from pyrogram.raw.types.auth.login_token_success import LoginTokenSuccess

from . import __version__


class Authorization:
    def __init__(self, test_mode: bool = False, qr_code: bool = True):
        api_id, api_hash = self.get_api_tokens()
        self.client = Client(
            "../teagram_v2",
            api_id=api_id,
            api_hash=api_hash,
            device_model="Windows 10",
            app_version=__version__,
            test_mode=test_mode,
        )
        self.qr_code = qr_code

    def get_api_tokens(self):
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
                api_prompt()
        except (NoSectionError, NoOptionError):
            api_prompt()

        with open("./config.ini", "w") as file:
            self.config.write(file)

        api_id = 0
        api_hash = "_"

        try:
            api_id = self.config.get("api_tokens", "api_id")
            api_hash = self.config.get("api_tokens", "api_hash")
        except Exception:
            pass

        return api_id, api_hash

    async def get_password(self):
        from getpass import getpass

        await self.client.invoke(GetPassword())
        while True:
            twofa = getpass("Enter 2FA password: ")
            try:
                await self.client.check_password(twofa)
                break
            except errors.PasswordHashInvalid:
                print("Invalid password, retrying...")
            except errors.FloodWait as err:
                print(f"Got floodwait retry after {err.value} seconds")

        return twofa

    async def get_phone_code(self):
        while True:
            try:
                phone = input("Enter phone number: ")
                return (phone, (await self.client.send_code(phone)).phone_code_hash)
            except errors.PhoneNumberInvalid:
                print("Invalid phone number, retrying...")
            except errors.PhoneNumberFlood as error:
                print(f"Phone floodwait, retry after: {error.value}")
            except errors.PhoneNumberBanned:
                print("Phone number banned, retrying...")
            except errors.PhoneNumberOccupied:
                print("Phone number occupied, retrying...")
            except errors.BadRequest:
                print("Bad request, retrying...")

    async def enter_phone_code(self, phone, phone_code_hash):
        code = input("Enter confirmation code: ")

        try:
            return await self.client.sign_in(
                phone, code, phone_code_hash=phone_code_hash
            )
        except errors.SessionPasswordNeeded:
            await self.get_password()
            return await self.enter_phone_code(phone, phone_code_hash)

    async def generate_qrcode(self, qrcode_token):
        from qrcode.main import QRCode
        from base64 import urlsafe_b64encode

        qrcode = QRCode(error_correction=1)
        qrcode.clear()
        qrcode.add_data(
            "tg://login?token={}".format(
                urlsafe_b64encode(qrcode_token.token).decode("utf-8").rstrip("=")
            )
        )
        qrcode.make()
        qrcode.print_ascii()

    async def authorize(self):
        await self.client.connect()

        try:
            me = await self.client.get_me()
        except errors.SessionRevoked:
            print("Session was terminated, deleting session...")
            from os import remove
            from sys import exit

            try:
                remove("teagram_v2.session")
            except PermissionError:
                print(
                    "No permissions, please remove session file by yourself and retry.."
                )

            await self.client.disconnect()
            return exit(64)
        except errors.AuthKeyUnregistered:
            me = None

        if not me:
            if not self.qr_code:
                phone, phone_hash = await self.get_phone_code()
                await self.enter_phone_code(phone, phone_hash)
            else:
                print("Logining with qrcode (--no-qrcode/-nqr to disable)")

                async def check_qr_status():
                    while True:
                        try:
                            qr_token = await self.client.invoke(
                                ExportLoginToken(
                                    api_id=self.client.api_id,
                                    api_hash=self.client.api_hash,
                                    except_ids=[],
                                )
                            )
                            if isinstance(qr_token, LoginTokenSuccess):
                                print("Success!")
                                return True

                            await asyncio.sleep(1)
                        except errors.SessionPasswordNeeded:
                            await self.get_password()
                            return True

                async def refresh_qr_code():
                    while True:
                        qr_token = await self.client.invoke(
                            ExportLoginToken(
                                api_id=self.client.api_id,
                                api_hash=self.client.api_hash,
                                except_ids=[],
                            )
                        )
                        if isinstance(qr_token, LoginToken):
                            print("Scan the QRCode below: ")
                            print(
                                "Settings > Privacy and Security > Active Sessions > Scan QR Code"
                            )

                            await self.generate_qrcode(qr_token)

                        await asyncio.sleep(30)

                status_task = asyncio.create_task(check_qr_status())
                refresh_task = asyncio.create_task(refresh_qr_code())

                await status_task
                refresh_task.cancel()

        await self.client.disconnect()
        return self.client
