from . import utils

from types import FunctionType
from inspect import getfullargspec, iscoroutine

from pyrogram import filters

from pyrogram.types import Message
from pyrogram.client import Client

from pyrogram.handlers import MessageHandler, EditedMessageHandler


class Dispatcher:
    def __init__(self, client, loader):
        self.client: Client = client

        self.database = loader.database
        self.loader = loader

    async def check_filter(self, function: FunctionType, message: Message):
        if filters := getattr(function, "filters", None):
            coroutine = filters(message)
            if iscoroutine(coroutine):
                await coroutine

            if not coroutine:
                return False
        else:
            return message.outgoing

        return True

    async def load(self):
        self.client.add_handler(
            handler=MessageHandler(self.handle_message, filters.all)
        )
        self.client.add_handler(
            handler=EditedMessageHandler(self.handle_message, filters.all)
        )

        return True

    async def handle_watchers(self, message: Message):
        for watcher in self.loader.watchers:
            if await self.check_filter(watcher, message):
                await watcher(message)

    async def handle_message(self, _, message: Message):
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
                f"<b>Message</b>: <code>{message.text}</code>\nError:\n<code>{error}</code>",
            )

        return message
