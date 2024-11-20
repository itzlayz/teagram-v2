import logging
import asyncio

from pyrogram import types
from pyrogram.errors import RPCError
from pyrogram.client import Client

from types import TracebackType
from typing import List, Union


class Conversation:
    def __init__(
        self, client: Client, chat_id: Union[str, int], purge: bool = False
    ) -> None:
        """

        :param app: Client
        :param chat_id: Chat's id
        :param purge: Delete or save message after conversation

        """
        self.client = client
        self.chat_id = chat_id
        self.purge = purge

        self.messages_to_purge: List[types.Message] = []

    async def __aenter__(self) -> "Conversation":
        return self

    async def __aexit__(
        self, exc_type: type, exc_value: Exception, exc_traceback: TracebackType
    ) -> bool:
        if all([exc_type, exc_value, exc_traceback]):
            logging.exception(exc_value)
        else:
            if self.purge:
                await self._purge()

        return self.messages_to_purge.clear()

    async def send_message(self, text: str, *args, **kwargs) -> types.Message:
        """
        :param text: Text to send
        :return: `types.Message`
        """
        message = await self.client.send_message(self.chat_id, text, *args, **kwargs)

        if self.purge:
            self.messages_to_purge.append(message)

        return message

    async def send_file(
        self, file_path: str, media_type: str, *args, **kwargs
    ) -> types.Message:
        """
        :param file_path: File path or url
        :param media_type: Type of media
        :return: `types.Message`
        """
        available_media = [
            "animation",
            "audio",
            "document",
            "photo",
            "sticker",
            "video",
            "video_note",
            "voice",
        ]
        if media_type not in available_media:
            raise TypeError(
                f"Invalid media_type, available media types: {''.join(available_media.keys())}"
            )

        message = await getattr(self.client, "send_" + media_type)(
            self.chat_id, file_path, *args, **kwargs
        )

        if self.purge:
            self.messages_to_purge.append(message)

        return message

    async def get_response(self, timeout: int = 30, limit: int = 1) -> types.Message:
        end_time = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < end_time:
            async for response in self.client.get_chat_history(
                self.chat_id, limit=limit
            ):
                if response.from_user and not response.from_user.is_self:
                    if self.purge:

                        self.messages_to_purge.append(response)

                    return response

            await asyncio.sleep(1)

        raise RuntimeError("Timeout has expired")

    async def _purge(self) -> bool:
        for message in self.messages_to_purge:
            try:
                await message.delete()
            except RPCError:
                logging.exception("Got error while purging messages")

        return True


class CustomClient(Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def conversation(self, chat_id: Union[str, int], purge: bool = False):
        return Conversation(self, chat_id, purge)
