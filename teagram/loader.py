import inspect
import logging

import sys
import os

from importlib.machinery import ModuleSpec
from importlib.util import spec_from_file_location, module_from_spec

from pyrogram.handlers.handler import Handler

from pathlib import Path

from .dispatcher import Dispatcher
from .types import Module, StringLoader

BASE_PATH = os.path.normpath(
    os.path.join(os.path.abspath(os.path.dirname(os.path.abspath(__file__))), "..")
)
MODULES_PATH = Path(os.path.join(BASE_PATH, "teagram/modules"))


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

    async def load_modules(self):
        for module in os.listdir(MODULES_PATH):
            if not module.endswith(".py"):
                continue

            path = os.path.join(os.path.abspath("."), MODULES_PATH, module)
            module_name = f"teagram.modules.{module[:-3]}"

            await self.load_module(module_name, path, origin="<core>")

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
                spec = StringLoader(module_source, origin)
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
        name = module_class.__class__.__name__

        self.prepare_module(module_class)
        if save_file and origin == "<string>" and module_source:
            path = os.path.join(MODULES_PATH.absolute(), f"{name}.py")
            with open(path, "w", encoding="UTF-8") as file:
                file.write(module_source)

        return module_class

    def prepare_module(self, module_class: Module):
        module_class.load_init()

        self.commands.update(module_class.commands)
        self.watchers.extend(module_class.watchers)

        self.raw_handlers.extend(module_class.raw_handlers)
        self.inline_handlers.extend(module_class.inline_handlers)
        self.callback_handlers.extend(module_class.callback_handlers)

        self.modules.append(module_class)
