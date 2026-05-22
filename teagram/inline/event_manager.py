from aiogram.types import Message, ChosenInlineResult, InlineQuery, CallbackQuery

from ..types import ABCLoader, Module
from .types import Form

from types import FunctionType

import typing
import inspect

import logging

logger = logging.getLogger(__name__)


class EventManager(Form):
    def __init__(self, loader: ABCLoader):
        self._loader = loader

    async def _check_filters(
        self,
        func: FunctionType,
        module: Module,
        event: typing.Union[Message, InlineQuery, CallbackQuery],
    ) -> bool:
        custom_filters = getattr(func, "_filters", None)
        if custom_filters and module:
            coro = custom_filters(module, event)
            if inspect.iscoroutine(coro):
                coro = await coro

            if not coro:
                return False
        elif event.from_user.id != self._loader.client.me.id:
            return False

        return True

    async def _message_handler(self, message: Message):
        logger.debug("Handling message from %s", message.from_user.as_json())

        for func in self._loader.message_handlers.copy():
            if not await self._check_filters(func, func.__self__, message):
                continue

            try:
                await func(message)
            except Exception:
                logger.exception("Error occurred while handling message")

        return message

    async def _callback_handler(self, callback_query: CallbackQuery):
        """Handles buttons' callback"""
        callback_data = callback_query.data

        logger.debug(
            "Handling %s from %s",
            callback_data,
            callback_query.from_user.as_json(),
        )

        if callback_data in self._forms:
            callback, args, kwargs = self._forms[callback_data]
            if await self._check_filters(callback, None, callback_query):
                try:
                    return await callback(callback_query, *args, **kwargs)
                except Exception:
                    logger.exception(
                        "Error occurred while handling registered callback query"
                    )

            return callback_query

        handler = self._loader.callback_handlers.get(callback_data)
        if handler:
            if await self._check_filters(handler, handler.__self__, callback_query):
                try:
                    await handler(callback_query)
                except Exception:
                    logger.exception("Error occurred while handling callback query")

                return callback_query

        for func in self._loader.callback_handlers.copy().values():
            if not await self._check_filters(func, func.__self__, callback_query):
                continue

            try:
                await func(callback_query)
            except Exception:
                logger.exception("Error occurred while handling callback query")

        return callback_query

    async def _inline_handler(self, inline_query: InlineQuery):
        """
        Handles inline queries like:
        `@pic tea`, `@teagram_v2 hidden_message secret`
        """
        query = inline_query.query
        cmd, args = query.split(maxsplit=1) if " " in query else (query, "")

        logger.debug("Handling %s from %s", query, inline_query.from_user.as_json())
        logger.debug("Command - `%s`, arguments - `%s`", cmd, args)

        form = self._forms.get(cmd)
        if form:
            try:
                return await self._form_inline_handler(inline_query, form)
            except Exception:
                logger.exception("Error occurred while handling form")

        func = self._loader.inline_handlers.get(cmd)
        if func:
            if await self._check_filters(func, func.__self__, inline_query):
                try:
                    result = await func(inline_query)
                    await self._handle_inline_result(inline_query, result)
                except Exception:
                    logger.exception("Error occurred while handling inline query")
        else:
            logger.debug("No inline handler found for %s", cmd)

        return query

    async def _chosen_inline_handler(self, chosen_inline_result: ChosenInlineResult):
        """Handles update when user clicking on inline query result"""
        chosen_query = chosen_inline_result.query

        logger.debug(
            "Handling chosen inline result for query: %s from user: %s",
            chosen_query,
            chosen_inline_result.from_user.as_json(),
        )

        # TODO: handle them fr
