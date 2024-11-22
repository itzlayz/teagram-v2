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
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("aiogram").setLevel(logging.ERROR)


class Main:
    def __init__(self, parser):
        self.parser = parser

    def start(self):
        try:
            import uvloop

            if sys.version_info[:2] >= (3, 12):
                uvloop.run(self.main())
            else:
                uvloop.install()
                asyncio.run(self.main())
        except ImportError:
            logging.info("Uvloop not found, it may cause perfomance leaks")
            asyncio.run(self.main())

    async def main(self):
        if getattr(self.parser, "debug", False):
            logging.getLogger().setLevel(logging.DEBUG)

        database = Database()

        client = await Authorization(
            getattr(self.parser, "test_mode", False),
            getattr(self.parser, "no_qr", False),
        ).authorize()

        await client.connect()
        await client.initialize()

        if not client.me:
            me = await client.get_me()
            client.me = me

        loader = Loader(client, database)
        await loader.load()

        await idle()
        logging.info("Shutdown...")
