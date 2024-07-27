import os
import time

import typing
import logging

from io import BytesIO, IOBase
from . import init_time

from pyrogram.types import Message
from pyrogram.enums.parse_mode import ParseMode

from enum import Enum
from urllib.parse import urlparse

FileLike = typing.Optional[typing.Union[BytesIO, IOBase, bytes, str]]
BASE_PATH = os.path.normpath(
    os.path.join(os.path.abspath(os.path.dirname(os.path.abspath(__file__))), "..")
)


class Parser(Enum):
    html = ParseMode.HTML
    markdown = ParseMode.MARKDOWN


def get_uptime() -> str:
    current_time = time.time()

    uptime_seconds = current_time - init_time

    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    hours, minutes, seconds = int(hours), int(minutes), int(seconds)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def get_command(database, message: Message):
    message.raw_text = getattr(message.raw, "message", message.text)
    prefixes = database.get("teagram", "prefix", ["."])

    for prefix in prefixes:
        if (
            message.raw_text
            and len(message.raw_text) > len(prefix)
            and message.raw_text.startswith(prefix)
        ):
            command, *args = message.raw_text[len(prefix) :].split(maxsplit=1)
            break
    else:
        return "", "", ""

    return prefix, command.lower(), args[-1] if args else ""


def normalize_parser(parse_mode):
    if isinstance(parse_mode, str):
        parse_mode = getattr(Parser, parse_mode.lower(), None)
        if parse_mode:
            return parse_mode.value

    return parse_mode


def is_url(url: str):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


async def answer(
    message: Message,
    data: typing.Union[str, FileLike],
    parse_mode: str = "HTML",
    **kwargs,
):
    result = None

    parse_mode = normalize_parser(parse_mode)
    caption = kwargs.pop("caption", None)

    if not data:
        logging.error("Error, you didn't pass data")
        return

    if data and not caption:
        if message.outgoing:
            result = await message.edit(data, parse_mode=parse_mode, **kwargs)
        else:
            result = await message.reply(data, parse_mode=parse_mode, **kwargs)
    elif caption:
        if not isinstance(data, (IOBase, BytesIO, bytes)) and not is_url(data):
            logging.error(f"Excepted `FileLike` got {type(data)}")
            return

        if isinstance(data, bytes):
            data = BytesIO(data)

        result = await message.reply_photo(
            data, caption=caption, parse_mode=parse_mode, **kwargs
        )
        if message.outgoing:
            await message.delete()

    return result
