from .auth import Authorization
from .loader import Loader

from .database import Database

from pyrogram.methods.utilities.idle import idle

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logging.getLogger().setLevel(logging.INFO)

LOGGERS = ["pyrogram", "aiogram", "aiohttp.access", "watchfiles.main"]
for logger in LOGGERS:
    logging.getLogger(logger).setLevel(logging.ERROR)


class Main:
    def __init__(self, arguments):
        self.arguments = arguments

    def start(self):
        try:
            import uvloop

            if sys.version_info[:2] >= (3, 12):
                uvloop.run(self.main())
            else:
                uvloop.install()
                asyncio.run(self.main())
        except ImportError:
            logging.info("Uvloop not installed, it may cause perfomance leaks")
            asyncio.run(self.main())

    async def main(self):
        if getattr(self.arguments, "debug", False):
            logging.getLogger().setLevel(logging.DEBUG)
            logging.getLogger("pyrogram").setLevel(logging.INFO)
            logging.getLogger("pyrogram.session").setLevel(logging.ERROR)

        database = Database()

        client = await Authorization(
            getattr(self.arguments, "test_mode", False),
            getattr(self.arguments, "no_qr", False),
            getattr(self.arguments, "no_web", False),
            getattr(self.arguments, "port", 0),
        ).authorize()

        await client.connect()
        await client.initialize()

        if not client.me:
            me = await client.get_me()
            client.me = me

        loader = Loader(client, database, self.arguments)
        await loader.load()

        await idle()
        logging.info("Shutdown...")
