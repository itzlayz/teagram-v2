#                            ██╗████████╗███████╗██╗░░░░░░█████╗░██╗░░░██╗███████╗
#                            ██║╚══██╔══╝╚════██║██║░░░░░██╔══██╗╚██╗░██╔╝╚════██║
#                            ██║░░░██║░░░░░███╔═╝██║░░░░░███████║░╚████╔╝░░░███╔═╝
#                            ██║░░░██║░░░██╔══╝░░██║░░░░░██╔══██║░░╚██╔╝░░██╔══╝░░
#                            ██║░░░██║░░░███████╗███████╗██║░░██║░░░██║░░░███████╗
#                            ╚═╝░░░╚═╝░░░╚══════╝╚══════╝╚═╝░░╚═╝░░░╚═╝░░░╚══════╝
#                                            https://t.me/itzlayz
#
#                                    🔒 Licensed under the Apache License
#                                 https://www.apache.org/licenses/LICENSE-2.0

import os
import re
import atexit
import asyncio

import logging

logger = logging.getLogger(__name__)


class ProxyTunnel:
    def __init__(self, port: int, proxy_created: asyncio.Event, *args, **kwargs):
        self.stream = None

        self.port = port
        self.proxy_created = proxy_created

        super().__init__(*args, **kwargs)

    def terminate(self):
        try:
            self.stream.terminate()
        except Exception as error:
            return False

        logger.debug("Stream terminated")

        return True

    async def create_proxy_tunnel(self):
        logger.info("Creating proxy tunnel...")

        url = None
        self.stream = await asyncio.create_subprocess_shell(
            f"ssh -R 80:localhost:{self.port} serveo.net",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        url = ""

        async def get_url():
            for line in iter(self.stream.stdout.readline, ""):
                line = (await line).decode()
                await asyncio.sleep(0.3)

                if match := re.search(
                    r"Forwarding HTTP traffic from (https://[^\s]+)", line
                ):
                    nonlocal url
                    url = match[1]

                    if not self.proxy_created.is_set():
                        self.proxy_created.set()

        asyncio.ensure_future(get_url())
        try:
            await asyncio.wait_for(self.proxy_created.wait(), 30)
        except Exception:
            pass

        if url:
            atexit.register(
                lambda: os.system(
                    f'kill $(pgrep -f "ssh -R 80:localhost:{self.port} serveo.net")'
                )
            )
            logger.info(f"Successfully created proxy. {url}")
        else:
            logger.error("Couldn't create tunnel proxy :(")
            logger.info(f"http://localhost:{self.port}")
