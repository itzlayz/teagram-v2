import inspect
import logging

import sys
import gc
import os
import re

from importlib.machinery import ModuleSpec
from importlib.util import spec_from_file_location, module_from_spec

from pyrogram.handlers.handler import Handler

from pathlib import Path
from typing import Final, List

from .utils import BASE_PATH
from . import __version__

from .dispatcher import Dispatcher
from .types import (
    Module,
    StringLoader,
    ModuleException,
    ModuleVersionException,
    ABCLoader,
)

from .inline import InlineDispatcher
from .translator import Translator, ModuleTranslator

MODULES_PATH = Path(os.path.join(BASE_PATH, "teagram/modules"))
CUSTOM_MODULES_PATH = Path(os.path.join(BASE_PATH, "teagram/custom_modules"))
CUSTOM_MODULES_PATH.mkdir(parents=True, exist_ok=True)


def set_attrs(func, *args, **kwargs):
    for arg in args:
        setattr(func, arg, True)

    for k, v in kwargs.items():
        setattr(func, k, v)

    return func


def command(custom_filters=None, *args, **kwargs):
    def decorator(func):
        if custom_filters:
            setattr(func, "_filters", custom_filters)

        return set_attrs(func, *args, **kwargs, is_command=True)

    return decorator


def watcher(custom_filters=None, *args, **kwargs):
    def decorator(func):
        if custom_filters:
            setattr(func, "_filters", custom_filters)

        return set_attrs(func, *args, **kwargs, is_watcher=True)

    return decorator


def raw_handler(handler: Handler, *args, **kwargs):
    def decorator(func):
        return set_attrs(func, *args, **kwargs, is_raw_handler=True, _handler=handler)

    return decorator


def inline_handler(custom_filters=None, *args, **kwargs):
    def decorator(func):
        if custom_filters:
            setattr(func, "_filters", custom_filters)

        return set_attrs(func, *args, **kwargs, is_inline_handler=True)

    return decorator


def callback_handler(custom_filters=None, *args, **kwargs):
    def decorator(func):
        if custom_filters:
            setattr(func, "_filters", custom_filters)

            print(func, func._filters)

        return set_attrs(func, *args, **kwargs, is_callback_handler=True)

    return decorator


def message_handler(custom_filters=None, *args, **kwargs):
    def decorator(func):
        if custom_filters:
            setattr(func, "_filters", custom_filters)

        return set_attrs(func, *args, **kwargs, is_message_handler=True)

    return decorator


class Loader(ABCLoader):
    def __init__(self, client, database, arguments):
        self.client = client
        self.database = database

        self.modules = []
        self.core_modules: Final[List[str]] = [
            "eval",
            "help",
            "info",
            "manager",
            "terminal",
        ]

        self.commands = {}
        self.aliases = {}

        self.raw_handlers = []
        self.watchers = []

        self.inline_handlers = {}
        self.callback_handlers = {}

        self.message_handlers = []

        self.dispatcher = Dispatcher(client, self)
        self.inline = InlineDispatcher(self)

        self.translator = Translator(self.database)

        if getattr(arguments, "hot_reload", False):
            self.start_watchdog()

    def get(self, key: str):
        return self.translator.get("loader", key)

    def _get_module_path(self, file_path: Path) -> str | None:
        if MODULES_PATH in file_path.parents:
            return f"teagram.modules.{file_path.stem}"
        elif CUSTOM_MODULES_PATH in file_path.parents:
            return f"teagram.custom_modules.{file_path.stem}"

        return None

    def start_watchdog(self):
        try:
            from .hot_reload import ModulesWatchdog

            self.watch_manager = ModulesWatchdog(
                self, [MODULES_PATH, CUSTOM_MODULES_PATH]
            )
            self.watch_manager.start()

            return True
        except ImportError:
            logging.exception(
                "To use hot-reload you need to install `dev_requirements.txt`"
            )

            return self.get("no_watchdog_library")

    async def load(self):
        await self.load_modules()

        await self.dispatcher.load()
        self.bot = await self.inline.load()

        logging.info("Loaded!")

    async def load_modules(self):
        for path in MODULES_PATH.glob("*.py"):
            module_name = f"teagram.modules.{path.stem}"
            if path.stem.lower() not in self.core_modules:
                logging.info(
                    f"Found custom module in core modules, please delete it to hide this message ({path})"
                )
                continue

            await self.load_module(module_name, path, origin="<core>")

        for path in CUSTOM_MODULES_PATH.glob("*.py"):
            module_name = f"teagram.custom_modules.{path.stem}"
            await self.load_module(module_name, path, origin="<custom>")

    async def load_module(
        self,
        module_name: str,
        file_path: str = "",
        spec: ModuleSpec = None,
        origin: str = "<string>",
        module_source: str = "",
        save_file: bool = False,
        watchdog: bool = False,
    ):
        if spec is None:
            if origin != "<core>":
                logging.debug("Module spec not found, trying to get manually..")

            if file_path:
                spec = spec_from_file_location(module_name, file_path)
            elif module_source:
                spec = ModuleSpec(
                    module_name, StringLoader(module_source, origin), origin=origin
                )
            else:
                return
        else:
            if not isinstance(spec, (ModuleSpec, StringLoader)):
                return

        module = module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        module_class = next(
            (
                value()
                for value in vars(module).values()
                if inspect.isclass(value) and issubclass(value, Module)
            ),
            None,
        )

        if not module_class:
            sys.modules.pop(module_name, None)

            raise ModuleException(self.get("module_class_not_found"))

        module_class.__origin__ = origin
        name = getattr(module_class, "name", module_class.__class__.__name__)

        min_version = module_class.MIN_VERSION
        if min_version != "BETA":
            if min_version != "Not specified":
                exception = ""
                if not re.fullmatch(r"\d+\.\d+\.\d+", min_version):
                    exception = self.get("invalid_module_min_version").format(
                        min_version
                    )

                current_version = tuple(map(int, __version__.split(".")))
                required_version = tuple(map(int, min_version.split(".")))

                if current_version < required_version:
                    exception = self.get("incompatible_version").format(
                        __version__, min_version
                    )

                if exception:
                    sys.modules.pop(module_name, None)
                    raise ModuleVersionException(exception)

        if self.lookup(name):
            if not watchdog:
                raise ModuleException(self.get("module_already_loaded").format(name))

            await self.unload_module(name, _watchdog=watchdog)

        self.prepare_module(module_class)
        if save_file and module_source:
            path = MODULES_PATH / f"{name}.py"
            path.write_text(module_source, encoding="UTF-8")

        await module_class.on_load()

        gc.collect()
        return module_class

    async def unload_module(self, module_name: str, *, _watchdog: bool):
        module = None
        for mod in self.modules:
            if module_name.lower() in mod.__class__.__name__.lower():
                module = mod
                break

        if module:
            if module.__origin__ == "<core>" and not _watchdog:
                raise ModuleException(self.get("unload_core_module_fault"))

            self.modules.remove(module)
            await module.on_unload()

            self.commands = {
                k: v for k, v in self.commands.items() if k not in module.commands
            }

            self.watchers = [w for w in self.watchers if w not in module.watchers]
            self.raw_handlers = [
                h for h in self.raw_handlers if h not in module.raw_handlers
            ]

            self.inline_handlers = {
                k: v
                for k, v in self.inline_handlers.items()
                if k not in module.inline_handlers
            }

            self.callback_handlers = {
                k: v
                for k, v in self.callback_handlers.items()
                if k not in module.callback_handlers
            }

            self.aliases = {
                k: v for k, v in self.aliases.items() if k not in module.commands.keys()
            }

        return module.__class__.__name__

    def prepare_module(self, module_class: Module):
        if module_class.__origin__ == "<core>":
            module_class.loader = self

        module_class.client = self.client
        module_class.database = self.database
        module_class.inline = self.inline

        module_class.load_init()
        module_class.translator = ModuleTranslator(
            module_class,
            self.translator,
            getattr(module_class, "strings", None),
        )

        self.commands.update(module_class.commands)
        self.watchers.extend(module_class.watchers)

        self.raw_handlers.extend(module_class.raw_handlers)
        self.inline_handlers.update(module_class.inline_handlers)
        self.callback_handlers.update(module_class.callback_handlers)

        self.message_handlers.extend(module_class.message_handlers)

        for name, command in module_class.commands.items():
            aliases = getattr(command, "alias", None)
            if isinstance(aliases, str):
                aliases = [aliases]

            if aliases:
                for alias in aliases:
                    self.aliases[alias] = name

        self.modules.append(module_class)

    def lookup(self, name: str):
        return next(
            (
                module
                for module in self.modules
                if module.__class__.__name__ == name
                or getattr(module, "name", "") == name
            ),
            None,
        )
