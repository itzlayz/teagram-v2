import logging
import asyncio

from base64 import b64decode, b64encode

from .token_manager import TokenManager
from .event_manager import EventManager

from ..types import ABCLoader

from aiogram import Bot, Dispatcher
from aiogram.utils.exceptions import ValidationError, Unauthorized


class InlineDispatcher(TokenManager, EventManager):
    def __init__(self, loader: ABCLoader):
        self._loader = loader
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

        self._forms = {}

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
            return await self.restart()

        try:
            await self.bot.delete_webhook(drop_pending_updates=True)

            self.dispatcher.register_message_handler(self._message_handler)
            self.dispatcher.register_callback_query_handler(self._callback_handler)
            self.dispatcher.register_inline_handler(self._inline_handler)
            self.dispatcher.register_chosen_inline_handler(self._chosen_inline_handler)

            asyncio.ensure_future(self.dispatcher.start_polling())
        except Unauthorized:
            return await self.restart()

        return self.bot

    async def restart(self):
        logging.error(f"Invalid token: {self.token}, revoking...")
        self.token = None

        return await self.load()

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
