from .. import loader, utils
from time import time

import atexit
import psutil

import sys
import os


def kill():
    if "DOCKER" in os.environ:
        sys.exit(0)
        return

    try:
        process = psutil.Process(os.getpid())
        for proc in process.children(recursive=True):
            proc.kill()

        sys.exit(0)
    except psutil.NoSuchProcess:
        pass


def restart(*_):
    print("Restarting...")

    os.execl(
        sys.executable,
        sys.executable,
        "-m",
        "teagram",
        *sys.argv[1:],
    )


class ManagerMod(loader.Module):
    async def on_load(self):
        data = self.database.get("teagram", "restart_info", None)
        if data:
            restart_time = round(time() - data["time"])
            message = await self.client.get_messages(data["chat"], data["id"])

            await utils.answer(
                message, f"<b>✅ Successfuly restarted ({restart_time}s)</b>"
            )
            self.database.pop("teagram", "restart_info")

    @loader.command()
    async def restart(self, message):
        message = await utils.answer(message, "<b>Restarting...</b>")
        atexit.register(restart)

        self.database.set(
            "teagram",
            "restart_info",
            {"chat": message.chat.id, "id": message.id, "time": time()},
        )

        kill()
