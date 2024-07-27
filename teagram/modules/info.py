from .. import loader, utils, __version__

import psutil
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

        return round(mem, 2)
    except Exception:
        return "Can't fetch"


class InfoMod(loader.Module):
    @loader.command()
    async def infocmd(self, message):
        ram = await get_ram()
        await utils.answer(
            message,
            (
                "<b>Teagram v2</b>\n\n"
                f"<b>RAM:</b> <code>{ram}MB</code>\n"
                f"<b>Uptime:</b> <code>{utils.get_uptime()}</code>\n"
                f"<b>Version:</b> <code>{__version__}</code>"
            ),
        )
