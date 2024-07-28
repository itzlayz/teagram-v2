from pyrogram.types import Message

from .. import loader, utils
from ..types import ModuleException

from time import time

import subprocess

import atexit
import psutil

import sys
import os

import git


def kill(force: bool = False):
    if "DOCKER" in os.environ:
        sys.exit(0)
        return

    try:
        process = psutil.Process(os.getpid())
        for proc in process.children(recursive=True):
            proc.kill()

        if force:
            process.kill()
        else:
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


class Manager(loader.Module):
    async def on_load(self):
        data = self.database.get("teagram", "restart_info", None)
        if data:
            restart_time = round(time() - data["time"])
            message = await self.client.get_messages(data["chat"], data["id"])

            await utils.answer(
                message, f"<b>✅ Successfuly restarted ({restart_time}s)</b>"
            )
            self.database.pop("teagram", "restart_info")

    def check_requirements(self, repo, sha):
        commit = repo.commit(sha)
        diffs = commit.diff(commit.parents[0])
        for diff in diffs:
            if diff.a_path == "requirements.txt" or diff.b_path == "requirements.txt":
                return self.download_requirements()

    def download_requirements(self):
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    "requirements.txt",
                    "--user",
                ],
                check=True,
            )
        except subprocess.CalledProcessError:
            print("Error during installing requirements.txt")

    async def load_module(
        self, code: str, save_file: bool = False, origin: str = "<string>"
    ):
        if utils.is_url(code):
            code = await self.fetch_code(code)

        module_class = await self.loader.load_module(
            f"teagram.custom_modules.{utils.random_id()}",
            module_source=code,
            origin=origin,
            save_file=save_file,
        )
        return module_class.__class__.__name__

    @loader.command()
    async def stop(self, message, args=None):
        await utils.answer(message, "<b>⏳ Stopping teagram...</b>")

        kill(True)

    @loader.command()
    async def restart(self, message):
        message = await utils.answer(message, "<b>⏳ Restarting...</b>")
        atexit.register(restart)

        self.database.set(
            "teagram",
            "restart_info",
            {"chat": message.chat.id, "id": message.id, "time": time()},
        )

        kill()

    @loader.command()
    async def update(self, message):
        message = await utils.answer(message, "<b>❔ Checking for update...</b>")

        try:
            repo = git.Repo(os.path.abspath("./.git"))
            branch = repo.active_branch.name

            local_commit = repo.head.commit.hexsha
            remote_commit = next(
                git.Repo().iter_commits(f"origin/{branch}", max_count=1)
            ).hexsha

            if local_commit == remote_commit:
                return await utils.answer(message, "<b>✅ Up to date</b>")

            repo.git.pull()
            self.check_requirements(repo, remote_commit)

            await self.restart(message)
        except git.exc.GitCommandError as e:
            return await utils.answer(
                message, f"<b>❌ Update failed:</b> <code>{str(e)}</code>"
            )
        except Exception as e:
            return await utils.answer(
                message,
                f"<b>❌ An unexpected error occurred:</b> <code>{str(e)}</code>",
            )

    @loader.command(alias="lm")
    async def loadmod(self, message: Message):
        reply = message.reply_to_message
        no_module = "<b>❌ No module specified, reply to message with module</b>"

        if not reply:
            return await utils.answer(message, no_module)

        file = reply.media
        if not file:
            return await utils.answer(message, no_module)

        path = await reply.download(in_memory=True)
        code = None

        if isinstance(file, str):
            try:
                with open(path, "r") as f:
                    code = f.read()
            except Exception as error:
                return await utils.answer(
                    message,
                    f"<b>❌ An unexpected error occurred</b> <code>{str(error)}</code>",
                )
        else:
            code = path.getvalue().decode()

        if not code:
            return await utils.answer(message, "<b>❌ File empty or corrupted</b>")

        try:
            module_name = await self.load_module(code)
            await utils.answer(
                message,
                f"<b>✅ Successfully loaded <code>{module_name}</code> module</b>",
            )
        except ModuleException as error:
            return await utils.answer(message, f"<b>{error}</b>")

    @loader.command(alias="ulm")
    async def unloadmod(self, message, args):
        module = args.strip()
        if not self.loader.lookup(module):
            return await utils.answer(message, "<b>❌ Module not found</b>")

        try:
            module_name = await self.loader.unload_module(module)
            if not module_name:
                return await utils.answer(
                    message, "<b>❌ Unexpected error occurred</b>"
                )
        except ModuleException as error:
            return await utils.answer(message, f"<b>{error}</b>")

        await utils.answer(
            message,
            f"<b>✅ Successfully unloaded <code>{module_name}</code> module</b>",
        )
