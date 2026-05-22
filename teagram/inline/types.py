import typing

from ..utils import FileLike, random_id
from ..types import ABCLoader

from aiogram import types

from pyrogram.types import Message as PyroMessage
from pyrogram.enums import ParseMode

from enum import Enum


class FormType(Enum):
    FORM = "form"

    # TODO: more types


class Form:
    def __init__(self, loader: ABCLoader):
        self._loader = loader

    # glitched don't use it
    async def answer(
        self,
        text: str,
        message: types.Message,
        reply_markup: typing.List[typing.Dict[str, typing.Any]] = None,
        *,
        photo: typing.Optional[FileLike] = None,
        gif: typing.Optional[FileLike] = None,
        video: typing.Optional[FileLike] = None,
        file: typing.Optional[FileLike] = None,
        audio: typing.Optional[FileLike] = None,
        parse_mode: typing.Optional[ParseMode] = ParseMode.HTML,
    ) -> types.Message:
        form_id = random_id()

        media = {
            k: v
            for k, v in {
                "photo": photo,
                "gif": gif,
                "video": video,
                "file": file,
                "audio": audio,
            }.items()
            if v is not None
        }

        self._forms[form_id] = {
            "type": FormType.FORM,
            "text": text,
            "message": message,
            "reply_markup": reply_markup,
            "parse_mode": parse_mode,
            **media,
        }

        bot_username = getattr(self, "bot_username", None)
        if not bot_username:
            me = await self.bot.get_me()
            bot_username = me.username

            self.bot_username = bot_username

        bot_results = await self._loader.client.get_inline_bot_results(
            bot_username, form_id
        )

        if isinstance(message, PyroMessage):
            reply_to_message_id = message.reply_to_message_id

        if isinstance(message, types.Message):
            reply_to_message_id = message.reply_to_message.message_id

        if bot_results and bot_results.results:
            return await self._loader.client.send_inline_bot_result(
                message.chat.id,
                bot_results.query_id,
                bot_results.results[0].id,
                reply_to_message_id=reply_to_message_id,
            )

    async def _form_inline_handler(
        self, inline_query: types.InlineQuery, form: typing.Dict
    ):
        normalized_markup = self._normalize_reply_markup(form.get("reply_markup"))
        base_text = form.get("text", "")
        parse_mode = "html"

        if form.get("photo"):
            result = {
                "type": "photo",
                "id": random_id(),
                "photo_url": form["photo"],
                "thumb_url": form.get("thumb_url", form["photo"]),
                "caption": base_text,
                "reply_markup": normalized_markup,
                "parse_mode": parse_mode,
            }
        elif form.get("gif"):
            result = {
                "type": "gif",
                "id": random_id(),
                "gif_url": form["gif"],
                "thumb_url": form.get("thumb_url", form["gif"]),
                "caption": base_text,
                "reply_markup": normalized_markup,
                "parse_mode": parse_mode,
            }
        elif form.get("video"):
            result = {
                "type": "video",
                "id": random_id(),
                "video_url": form["video"],
                "thumb_url": form.get("thumb_url", form["video"]),
                "caption": base_text,
                "reply_markup": normalized_markup,
                "parse_mode": parse_mode,
            }
        elif form.get("file"):
            result = {
                "type": "document",
                "id": random_id(),
                "document_url": form["file"],
                "thumb_url": form.get("thumb_url", form["file"]),
                "caption": base_text or "Teagram",
                "reply_markup": normalized_markup,
                "parse_mode": parse_mode,
            }
        elif form.get("audio"):
            result = {
                "type": "audio",
                "id": random_id(),
                "audio_url": form["audio"],
                "title": form.get("title", "Teagram"),
                "performer": form.get("performer", ""),
                "reply_markup": normalized_markup,
                "parse_mode": parse_mode,
            }
        else:
            result = {
                "type": "article",
                "id": random_id(),
                "title": form.get("title", "Teagram"),
                "description": base_text,
                "reply_markup": normalized_markup,
                "parse_mode": parse_mode,
            }

        if "message" not in result and "input_message_content" not in result:
            result["message"] = base_text

        result["input_message_content"] = self._normalize_input_message_content(
            result.copy()
        )

        await inline_query.answer([result], cache_time=30)

    async def _handle_inline_result(
        self, inline_query: types.InlineQuery, func_results: typing.List[typing.Dict]
    ):
        if func_results and isinstance(func_results, list):
            results = []
            for result in func_results:
                if "reply_markup" in result:
                    result["reply_markup"] = self._normalize_reply_markup(
                        result["reply_markup"]
                    )

                result["input_message_content"] = self._normalize_input_message_content(
                    result
                )

                results.append(result)

            return await inline_query.answer(results, cache_time=30)

        await inline_query.answer([], cache_time=0)

    def _normalize_input_message_content(self, result: dict) -> dict:
        content = result.pop("input_message_content", result.pop("message", None))
        if content:
            return {"message_text": content} if isinstance(content, str) else content

        input_type = result.get("input_type")
        if input_type == "location":
            return {
                "latitude": result.pop("latitude"),
                "longitude": result.pop("longitude"),
            }
        elif input_type == "contact":
            return {
                "phone_number": result.pop("phone_number"),
                "first_name": result.pop("first_name"),
                "last_name": result.pop("last_name", None),
            }
        elif input_type == "audio":
            return {
                "audio_url": result.pop("audio_url"),
                "performer": result.pop("performer", ""),
                "title": result.pop("title", ""),
            }
        elif input_type in ("gif", "animation"):
            return {
                "animation_url": result.pop("gif_url", result.pop("animation_url", "")),
                "caption": result.pop("caption", ""),
            }
        elif input_type == "video":
            return {
                "video_url": result.pop("video_url"),
                "caption": result.pop("caption", ""),
            }
        elif input_type == "file":
            return {
                "document_url": result.pop("document_url"),
                "caption": result.pop("caption", ""),
            }

        return {}

    def _normalize_reply_markup(self, reply_markup):
        if (
            isinstance(reply_markup, dict) and "inline_keyboard" in reply_markup
        ) or not reply_markup:
            return reply_markup

        if isinstance(reply_markup, list):
            keyboard = []
            for row in reply_markup:
                normalized_row = []
                for button in row:
                    if "callback" in button and callable(button["callback"]):
                        callback_func = button.pop("callback")
                        args = button.pop("args", [])
                        kwargs = button.pop("kwargs", {})

                        button["callback_data"] = self._register_callback(
                            callback_func, args, kwargs
                        )

                    normalized_row.append(button)

                keyboard.append(normalized_row)

            return {"inline_keyboard": keyboard}

        return reply_markup

    def _register_callback(self, callback, args, kwargs):
        callback_id = str(hash((callback, tuple(args), frozenset(kwargs.items()))))
        self._forms[callback_id] = (callback, args, kwargs)

        return callback_id
