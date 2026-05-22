import asyncio
import logging

from pathlib import Path
from watchfiles import awatch


class ModulesWatchdog:
    def __init__(self, loader, paths: list):
        self.loader = loader
        self.paths = paths
        self.task = None

    async def _watch(self):
        async for changes in awatch(*[str(p) for p in self.paths], recursive=False):
            for change, file_path in changes:
                if not file_path.endswith(".py"):
                    continue

                file_path_obj = Path(file_path)
                module_name = self.loader._get_module_path(file_path_obj)

                if module_name:
                    logging.debug(f"Detected change in {module_name}")
                    await self.loader.load_module(module_name, file_path, watchdog=True)

    def start(self):
        self.task = asyncio.create_task(self._watch())
        logging.debug("Watchdog started.")

    def stop(self):
        if self.task:
            self.task.cancel()
            logging.debug("Watchdog stopped.")

            del self.task
