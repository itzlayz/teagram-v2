from pyrogram.types import Message

from .. import loader, utils

from ..translator import SUPPORTED_LANGUAGES
from ..types import ModuleException

from time import time

import subprocess
import logging

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
    logging.info("Restarting...")

    os.execl(
        sys.executable,
        sys.executable,
        "-m",
        "teagram",
        *sys.argv[1:],
    )


class Manager(loader.Module):
    strings = {"name": "Manager"}

    async def on_load(self):
        data = self.database.get("teagram", "restart_info", None)
        if data:
            restart_time = round(time() - data["time"])
            message = await self.client.get_messages(data["chat"], data["id"])

            await utils.answer(
                message, self.get("restart_success").format(restart_time)
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
            logging.error("Error during installing requirements.txt")

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
        await utils.answer(message, self.get("stopping"))

        kill(True)

    @loader.command()
    async def restart(self, message):
        message = await utils.answer(message, self.get("restarting"))
        atexit.register(restart)

        self.database.set(
            "teagram",
            "restart_info",
            {"chat": message.chat.id, "id": message.id, "time": time()},
        )

        kill()

    @loader.command()
    async def update(self, message):
        message = await utils.answer(message, self.get("checking_updates"))

        try:
            repo = git.Repo(os.path.abspath("."))
            branch = repo.active_branch.name

            repo.remotes.origin.fetch()

            local_commit = repo.head.commit.hexsha
            remote_commit = next(
                repo.iter_commits(f"origin/{branch}", max_count=1)
            ).hexsha

            if local_commit == remote_commit:
                return await utils.answer(message, self.get("uptodate"))

            repo.git.pull()
            self.check_requirements(repo, remote_commit)

            await self.restart(message)
        except git.exc.GitCommandError as e:
            return await utils.answer(message, self.get("update_fail").format(e))
        except Exception as e:
            return await utils.answer(message, self.get("unexpected_error").format(e))

    @loader.command(alias="lm")
    async def loadmod(self, message: Message):
        reply = message.reply_to_message
        module_not_found = self.get("module_not_found")

        if not reply:
            return await utils.answer(message, module_not_found)

        file = reply.media
        if not file:
            return await utils.answer(message, module_not_found)

        path = await reply.download(in_memory=True)
        code = None

        if isinstance(file, str):
            try:
                with open(path, "r") as f:
                    code = f.read()
            except Exception as error:
                return await utils.answer(
                    message, self.get("unexpected_error").format(error)
                )
        else:
            code = path.getvalue().decode()

        if not code:
            return await utils.answer(message, self.get("empty_file"))

        try:
            module_name = await self.load_module(code)
            await utils.answer(message, self.get("load_success").format(module_name))
        except ModuleException as error:
            return await utils.answer(message, f"<b>{error}</b>")

    @loader.command(alias="ulm")
    async def unloadmod(self, message, args):
        module = args.strip()
        if not self.loader.lookup(module):
            return await utils.answer(message, self.get("module_not_found"))

        try:
            module_name = await self.loader.unload_module(module)
            if not module_name:
                return await utils.answer(message, self.get("unexpected_error"))
        except ModuleException as error:
            return await utils.answer(message, f"<b>{error}</b>")

        await utils.answer(message, self.get("unload_success").format(module_name))

    @loader.command()
    async def setlang(self, message, args: str):
        language = args.strip().lower()
        if language not in SUPPORTED_LANGUAGES:
            return await utils.answer(
                message,
                self.get("language_not_supported").format(
                    ", ".join(SUPPORTED_LANGUAGES)
                ),
            )

        self.loader.translator.language = language
        await utils.answer(message, self.get("set_lang_success").format(language))
