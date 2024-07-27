from .. import loader, utils

from pyrogram.types import Message
from typing import List

import time
import asyncio


class Terminal:
    BUFFER = 8192
    UPDATE_INTERVAL = 0.25

    def __init__(self, message: Message):
        self.message = message
        self.last_update = time.time_ns()

        self.stdout = ""
        self.stderr = ""

        self.finished = asyncio.Event()

    async def run(self, command: str):
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        await self.message.edit("Running command...")

        stdout_task = asyncio.create_task(self._read_stream(process.stdout, "STDOUT"))
        stderr_task = asyncio.create_task(self._read_stream(process.stderr, "STDERR"))

        await process.wait()

        await stdout_task
        await stderr_task

        self.finished.set()

    async def _read_stream(self, stream: asyncio.StreamReader, stream_name: str):
        while True:
            chunk = await stream.read(self.BUFFER)
            if not chunk:
                break

            output = chunk.decode("utf-8")
            if stream_name == "STDOUT":
                self.stdout += output
            else:
                self.stderr += output

            await self._update_message()

    async def _update_message(self):
        current_time = time.time_ns()
        if current_time - self.last_update >= self.UPDATE_INTERVAL:
            self.last_update = current_time

            self.message = await utils.answer(
                self.message,
                f"STDOUT:\n<code>{self.stdout}</code>\n\nSTDERR:\n<code>{self.stderr}</code>",
            )


class TerminalMod(loader.Module):
    def __init__(self):
        self.terminals: List[Terminal] = []

    @loader.command()
    async def bash(self, message: Message, args: str):
        command = args.strip()
        terminal = Terminal(message)

        self.terminals.append(terminal)
        await terminal.run(command)

        try:
            await asyncio.wait_for(terminal.finished.is_set())
        except Exception:
            pass

        try:
            self.terminals.remove(terminal)
        except ValueError:
            pass
