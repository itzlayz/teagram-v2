from .auth import Authorization
from .loader import Loader

from .database import Database
from pyrogram.methods.utilities.idle import idle

import asyncio
import sys


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
            print("Uvloop not found, it may cause perfomance leaks")
            asyncio.run(self.main())

    async def main(self):
        database = Database()

        client = await Authorization().authorize()
        await client.connect()
        await client.initialize()

        loader = Loader(client, database)
        await loader.load()

        if not client.me:
            me = await client.get_me()
            client.me = me

        await idle()
        print("Shutdown...")
