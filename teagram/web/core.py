import asyncio
import atexit

from . import proxy, websocket

import os
import sys


class WebCore(websocket.WebsocketServer, proxy.ProxyTunnel):
    def __init__(self, port: int = 8080, test_mode: bool = False):
        self.port = port
        self.test_mode = test_mode

        self.login_success = asyncio.Event()
        self.proxy_created = asyncio.Event()

        super().__init__(
            port=port,
            test_mode=test_mode,
            proxy_created=self.proxy_created,
            login_success=self.login_success,
        )

    async def run(self):
        await self.start_server(self.port)
        await self.get_proxy()

        await asyncio.wait_for(self.login_success.wait(), None)
        return self.client
