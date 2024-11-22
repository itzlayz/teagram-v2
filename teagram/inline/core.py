import logging
import asyncio

from base64 import b64decode, b64encode

from .token_manager import TokenManager
from ..types import ABCLoader

from aiogram import Bot, Dispatcher
from aiogram.utils.exceptions import ValidationError


class InlineDispatcher(TokenManager):
    def __init__(self, loader: ABCLoader):
        self.loader = loader
        self.client = loader.client
        self.database = loader.database

        self.token = self.database.get("teagram", "inline_token", None)

        if self.token and not self.is_base64(self.token):
            self.token = self.encode_token(self.token)
            self.database.set("teagram", "inline_token", self.token)

        if self.token:
            self.token = self.decode_token(self.token)

        self.bot: Bot = None
        self.dispatcher: Dispatcher = None

    async def on_startup(self, *_):
        logging.debug("Inline dispatcher started")

    async def load(self):
        if not self.token:
            self.token = await self.revoke_token()
            self.set_token(self.token)

        try:
            self.bot = Bot(self.token)
            self.dispatcher = Dispatcher(self.bot)
        except ValidationError:
            logging.error(f"Invalid token: {self.token}, revoking...")
            self.token = None

            return await self.load()

        await self.bot.delete_webhook(drop_pending_updates=True)
        asyncio.ensure_future(self.dispatcher.start_polling())

        return self.bot

    def is_base64(self, s: str) -> bool:
        try:
            b64decode(s)
            return True
        except Exception:
            return False

    def encode_token(self, token: str) -> str:
        return b64encode(token.encode("utf-8")).decode("utf-8")

    def decode_token(self, token: str) -> str:
        return b64decode(token).decode("utf-8")

    def set_token(self, token: str):
        self.database.set("teagram", "inline_token", self.encode_token(token))
