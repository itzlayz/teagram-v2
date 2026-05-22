import os
import time

import typing
import logging

import random
import string

from io import BytesIO, IOBase
from . import init_time

from pyrogram.types import Message
from pyrogram.enums.parse_mode import ParseMode

from aiogram import types

from enum import Enum
from urllib.parse import urlparse

FileLike = typing.Optional[typing.Union[BytesIO, IOBase, bytes, str]]
InlineLike = typing.Union[
    types.ChosenInlineResult, types.InlineQuery, types.CallbackQuery
]

BASE_PATH = os.path.normpath(
    os.path.join(os.path.abspath(os.path.dirname(os.path.abspath(__file__))), "..")
)
LETTERS = (
    string.ascii_letters
    + string.ascii_lowercase
    + string.ascii_uppercase
    + string.digits
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
    content: typing.Union[str, FileLike],
    parse_mode: str = "HTML",
    **kwargs,
):
    result = None

    parse_mode = normalize_parser(parse_mode)
    caption = kwargs.pop("caption", None)

    if not content:
        logging.error(f"Expected content got {content}")
        return

    if content and not caption:
        if message.outgoing:
            result = await message.edit(content, parse_mode=parse_mode, **kwargs)
        else:
            result = await message.reply(content, parse_mode=parse_mode, **kwargs)
    elif caption:
        if not isinstance(content, (IOBase, BytesIO, bytes)) and not is_url(content):
            logging.error(f"Expected `FileLike` got {type(content)}")
            return

        if isinstance(content, bytes):
            content = BytesIO(content)

        result = await message.reply_photo(
            content, caption=caption, parse_mode=parse_mode, **kwargs
        )
        if message.outgoing:
            await message.delete()

    return result


def random_id(length: int = 10):
    return "".join(random.choice(LETTERS) for _ in range(length))


def clear_console():
    """Simulation of clear console, moves cursor to last line of command line. Compatible with all systems"""
    print("\033[H\033[J", end="")


rand = random_id
