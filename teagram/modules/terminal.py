from .. import loader, utils

from pyrogram.types import Message
from typing import List

import time
import asyncio


class Stream:
    BUFFER = 8192
    UPDATE_INTERVAL = 0.25

    def __init__(self, message: Message, get):
        self.get = get  # brainrot

        self.message = message
        self.last_update = time.time_ns()

        self.stdout = ""
        self.stderr = ""

        self.finished = asyncio.Event()
        self.process = None

    async def run(self, command: str):
        self.process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        self.command = command

        await self.message.edit(self.get("running_command").format(self.command))

        stdout_task = asyncio.create_task(
            self._read_stream(self.process.stdout, "STDOUT")
        )
        stderr_task = asyncio.create_task(
            self._read_stream(self.process.stderr, "STDERR")
        )

        await self.process.wait()

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
            text = (
                self.get("command").format(self.command)
                + f'<b>🖥️ STDOUT:</b>\n<pre language="shell">{self.stdout}</pre>\n'
            )
            if self.stderr:
                text += f"<b><emoji id=5210952531676504517>❌</emoji> STDERR:</b>\n<pre>{self.stderr}</pre>"

            self.message = await utils.answer(self.message, text)

    async def terminate(self):
        if self.process and self.process.returncode is None:
            self.process.terminate()
            await self.process.wait()

            text = (
                self.get("terminated")
                + self.get("command").format(self.command)
                + f'<b>🖥️ STDOUT:</b>\n<pre language="shell">{self.stdout}</pre>\n'
            )

            if self.stderr:
                text += f"<b><emoji id=5210952531676504517>❌</emoji> STDERR:</b>\n<pre>{self.stderr}</pre>"

            await utils.answer(self.message, text)


class Terminal(loader.Module):
    strings = {"name": "Terminal"}

    def __init__(self):
        self.terminals: List[Stream] = []

    @loader.command(alias=["terminal", "t"])
    async def bash(self, message: Message, args: str):
        command = args.strip()
        terminal = Stream(message, self.get)

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

    @loader.command()
    async def kill(self, message: Message):
        reply = message.reply_to_message
        terminal = next(
            (
                terminal
                for terminal in self.terminals
                if getattr(reply, "id", "") == terminal.message.id
            ),
            None,
        )

        if not reply or not terminal:
            return await utils.answer(message, self.get("no_reply"))

        await terminal.terminate()
        if message.outgoing:
            await message.delete()
