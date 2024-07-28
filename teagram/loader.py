import inspect
import logging

import sys
import gc
import os

from importlib.machinery import ModuleSpec
from importlib.util import spec_from_file_location, module_from_spec

from pyrogram.handlers.handler import Handler

from pathlib import Path
from typing import Final, List

from .utils import BASE_PATH

from .dispatcher import Dispatcher
from .types import Module, StringLoader, ModuleException

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
            setattr(func, "filters", custom_filters)

        return set_attrs(func, *args, **kwargs, is_command=True)

    return decorator


def watcher(custom_filters=None, *args, **kwargs):
    def decorator(func):
        if custom_filters:
            setattr(func, "filters", custom_filters)

        return set_attrs(func, *args, **kwargs, is_watcher=True)

    return decorator


def raw_handler(handler: Handler, *args, **kwargs):
    def decorator(func):
        return set_attrs(func, *args, **kwargs, is_raw_handler=True, _handler=handler)

    return decorator


def inline_handler(custom_filters=None, *args, **kwargs):
    def decorator(func):
        if custom_filters:
            setattr(func, "filters", custom_filters)

        return set_attrs(func, *args, **kwargs, is_inline_handler=True)

    return decorator


def callback_handler(custom_filters=None, *args, **kwargs):
    def decorator(func):
        if custom_filters:
            setattr(func, "filters", custom_filters)

        return set_attrs(func, *args, **kwargs, is_callback_handler=True)

    return decorator


class Loader:
    def __init__(self, client, database):
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

        self.inline_handlers = []
        self.callback_handlers = []

        self.dispatcher = Dispatcher(client, self)

    async def load(self):
        await self.load_modules()
        await self.dispatcher.load()

        print("Loaded!")

    async def load_modules(self):
        for path in MODULES_PATH.glob("*.py"):
            module_name = f"teagram.modules.{path.stem}"
            if path.stem.lower() not in self.core_modules:
                print(
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
            )
        )

        module_class.__origin__ = origin
        name = getattr(module_class, "name", module_class.__class__.__name__)

        if self.lookup(name):
            raise ModuleException(f"❌ Module {name} has already loaded")

        self.prepare_module(module_class)
        if save_file and module_source:
            path = MODULES_PATH / f"{name}.py"
            path.write_text(module_source, encoding="UTF-8")

        await module_class.on_load()
        return module_class

    async def unload_module(self, module_name: str):
        module = None
        for mod in self.modules:
            if module_name.lower() in mod.__class__.__name__.lower():
                module = mod
                break

        if module:
            if module.__origin__ == "<core>":
                raise ModuleException("❌ Core module can't be unloaded")

            self.modules.remove(module)
            await module.on_unload()

            self.commands = {
                k: v for k, v in self.commands.items() if k not in module.commands
            }

            self.watchers = [w for w in self.watchers if w not in module.watchers]
            self.raw_handlers = [
                h for h in self.raw_handlers if h not in module.raw_handlers
            ]
            self.inline_handlers = [
                h for h in self.inline_handlers if h not in module.inline_handlers
            ]
            self.callback_handlers = [
                h for h in self.callback_handlers if h not in module.callback_handlers
            ]

            self.aliases = {
                k: v for k, v in self.aliases.items() if k not in module.commands.keys()
            }

        gc.collect()
        return module.__class__.__name__

    def prepare_module(self, module_class: Module):
        module_class.client = self.client
        module_class.database = self.database
        module_class.loader = self

        module_class.load_init()

        self.commands.update(module_class.commands)
        self.watchers.extend(module_class.watchers)

        self.raw_handlers.extend(module_class.raw_handlers)
        self.inline_handlers.extend(module_class.inline_handlers)
        self.callback_handlers.extend(module_class.callback_handlers)

        for name, command in module_class.commands.items():
            aliases = getattr(command, "alias", None)
            if isinstance(aliases, str):
                aliases = [aliases]

            if aliases:
                for alias in aliases:
                    self.aliases[alias] = name

        if module_class.__origin__ == "<core>":
            module_class.loader = self

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
