from .. import loader, utils, __version__
from aiogram.types import InputFile

import psutil
import time
import os

import asyncio


async def get_ram() -> float:
    try:
        loop = asyncio.get_running_loop()
        process = psutil.Process(os.getpid())

        mem = await loop.run_in_executor(None, process.memory_info)
        mem = mem[0] / 2.0**20

        children = await loop.run_in_executor(None, process.children, True)
        child_mems = await asyncio.gather(
            *[loop.run_in_executor(None, child.memory_info) for child in children]
        )

        for child_mem in child_mems:
            mem += child_mem[0] / 2.0**20

        return f"{round(mem, 2)}MB"
    except Exception as error:
        return str(error)


async def get_cpu() -> str:
    try:
        loop = asyncio.get_running_loop()
        process = psutil.Process(os.getpid())

        cpu = await loop.run_in_executor(None, process.cpu_percent, None)
        children = await loop.run_in_executor(None, process.children, True)
        child_cpus = await asyncio.gather(
            *[loop.run_in_executor(None, child.cpu_percent) for child in children]
        )

        cpu += sum(child_cpus)

        return f"{cpu:0.2f}%"
    except Exception as error:
        return str(error)


class Info(loader.Module):
    strings = {"name": "Info"}

    @loader.command()
    async def infocmd(self, message):
        await utils.answer(
            message,
            (
                "<b>☕️ Teagram v2</b>\n\n"
                f"<b>🧠 {self.get('ram')}:</b> <code>{(await get_ram())}</code>\n"
                f"<b>⚡ {self.get('cpu')}:</b> <code>{(await get_cpu())}</code>\n\n"
                f"<b>⏳ {self.get('uptime')}:</b> <code>{utils.get_uptime()}</code>\n"
                f"<b>💭 {self.get('version')}:</b> <code>{__version__}</code>"
            ),
        )

    @loader.command()
    async def pingcmd(self, message):
        start_time = time.perf_counter_ns()
        message = await utils.answer(message, "☕")

        ping = round((time.perf_counter_ns() - start_time) / 10**6, 3)

        await utils.answer(message, self.get("ping").format(ping))

    @loader.message_handler(lambda _, message: "start" in message.text.lower())
    async def start_message_handler(self, message):
        await message.answer_photo(
            photo=InputFile("assets/teagram_banner.png"),
            caption=self.get("hello_world").format(
                self.database.get("teagram", "prefix", ["."])[0]
            ),
            parse_mode="HTML",
            reply_markup={
                "inline_keyboard": [
                    [
                        {
                            "text": "💻 Github",
                            "url": "https://github.com/itzlayz/teagram-v2",
                        }
                    ]
                ]
            },
        )
