from . import utils

from types import FunctionType
from inspect import getfullargspec, iscoroutine

from pyrogram import filters

from pyrogram.types import Message
from pyrogram.client import Client

from pyrogram.handlers import MessageHandler, EditedMessageHandler, RawUpdateHandler

import logging

logger = logging.getLogger(__name__)


class Dispatcher:
    def __init__(self, client, loader):
        self.client: Client = client

        self.database = loader.database
        self.loader = loader

    async def check_filter(self, function: FunctionType, message: Message):
        filters = getattr(function, "_filters", None)

        if filters:
            coroutine = filters(message)
            if iscoroutine(coroutine):
                await coroutine

            if not coroutine:
                return False
        else:
            return message.outgoing or (
                message.from_user and message.from_user.id == self.client.me.id
            )

        return True

    async def load(self):
        self.client.add_handler(
            handler=MessageHandler(self.handle_message, filters.all)
        )
        self.client.add_handler(
            handler=EditedMessageHandler(self.handle_message, filters.all)
        )
        self.client.add_handler(
            handler=RawUpdateHandler(self.handle_raw_update, filters.all)
        )

        return True

    async def handle_watchers(self, message: Message):
        for watcher in self.loader.watchers:
            try:
                if await self.check_filter(watcher, message):
                    await watcher(message)
            except Exception:
                logger.exception("Error occurred while handling watcher")

    async def handle_message(self, _, message: Message):
        await self.handle_watchers(message)

        _, command, args = utils.get_command(self.database, message)
        if not (command or args):
            return

        command = self.loader.aliases.get(command, command)
        func = self.loader.commands.get(command.lower())

        if not func or not await self.check_filter(func, message):
            return

        try:
            vars_ = getfullargspec(func).args
            if len(vars_) > 2:
                await func(message, args)
            else:
                await func(message)
        except Exception as error:
            import traceback

            error = "\n".join(traceback.format_exception(error))

            await utils.answer(
                message,
                f"<b><emoji id=5210952531676504517>❌</emoji>An unexpected error occurred while executing command</b>: <code>{message.text}</code>\n"
                f"<b>❔ Error:</b>\n<code>{error}</code>",
            )

        return message

    async def handle_raw_update(self, update, *args, **kwargs):
        for handler in self.loader.raw_handlers:
            try:
                if await self.check_filter(handler, update):
                    await handler(update, *args, **kwargs)
            except Exception:
                logger.exception("Error occurred while handling raw update")
