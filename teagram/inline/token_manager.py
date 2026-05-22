from ..client import CustomClient
from ..types import ABCLoader

from ..utils import rand

from pyrogram import errors
from re import search

import logging
import asyncio


class TokenManager:
    def __init__(self, loader: ABCLoader):
        self._loader = loader
        self.client: CustomClient = loader.client

    async def cancel(self, conversation):
        try:
            await conversation.send_message("/cancel")
            await conversation.get_response()
        except errors.UserIsBlocked:
            await self.client.unblock_user("@BotFather")

            await conversation.send_message("/cancel")
            await conversation.get_response()

    async def prepare_bot(self, conversation, bot_username: str):
        for command in [
            "/setinline",
            bot_username,
            f"teagram@{self.client.me.username}:~$",
            "/setuserpic",
            bot_username,
        ]:
            await conversation.send_message(command)
            await asyncio.sleep(0.5)

        await conversation.send_file("assets/bot_avatar.png", media_type="photo")
        await conversation.get_response()

        async with self.client.conversation(bot_username) as conversation:
            await conversation.send_message("/start")

    async def create_bot(self):
        async with self.client.conversation("@BotFather", purge=True) as conversation:
            await self.cancel(conversation)

            await conversation.send_message("/newbot")
            response = await conversation.get_response()

            if not all(
                error not in response.text.lower()
                for error in ["sorry", "cannot", "can't"]
            ):
                logging.error(response.text)

                if "too many attempts" in response.text:
                    seconds = response.text.split()[-2]
                    logging.error(f"Sleeping for {seconds} seconds...")

                    await asyncio.sleep(int(seconds))
                    return await self.create_bot()

                if "20" in response.text:
                    logging.error(
                        "Bot limit reached, delete some of your bots and restart."
                    )
                    exit()

                await asyncio.sleep(5)
                return await self.create_bot()

            await conversation.send_message(
                f"Teagram userbot of {self.client.me.username[:30]}"
            )
            await conversation.get_response()

            bot_username = f"@teagram_v2_{rand(5)}_bot"
            await conversation.send_message(bot_username)

            await asyncio.sleep(0.5)
            response = await conversation.get_response()

            token = search(r"(?<=<code>)(.*?)(?=</code>)", response.text.html)
            if not token:
                logging.error(response.text)
                await asyncio.sleep(5)

                return await self.create_bot()

            logging.info("Successfully created inline bot!")

            token = token.group(0)
            await self.prepare_bot(conversation, bot_username)

        return token

    async def revoke_token(self):
        async with self.client.conversation("@BotFather") as conversation:
            await self.cancel(conversation)

            await conversation.send_message("/mybots")
            message = await conversation.get_response()

            bot_username = None

            while not bot_username:
                try:
                    message = await self.client.get_messages(
                        message.chat.id, message.id
                    )

                    for row in getattr(message.reply_markup, "inline_keyboard", []):
                        for button in row:
                            if button.text.startswith("@teagram_v2_"):
                                bot_username = button.text
                                break

                            if button.text == "»":
                                await asyncio.sleep(0.25)
                                await self.client.request_callback_answer(
                                    message.chat.id,
                                    message.id,
                                    getattr(button, "data", button.callback_data),
                                )
                                break

                            if button.text == "«":
                                bot_username = -1
                                break

                        if bot_username:
                            break

                    if bot_username:
                        break

                except Exception:
                    logging.exception("Send this error to teagram chat support")
                    return exit()

                await asyncio.sleep(0.5)

            if not bot_username or bot_username == -1:
                logging.info("Teagram bot not found, creating new one...")
                return await self.create_bot()

            await self.prepare_bot(conversation, bot_username)

            await conversation.send_message("/cancel")
            await conversation.get_response()

            await conversation.send_message("/revoke")
            await conversation.get_response()

            await conversation.send_message(bot_username)
            message = await conversation.get_response()

            token = message.text.split("\n")[-1]

            logging.info("Successfully revoked inline token!")

        return token
