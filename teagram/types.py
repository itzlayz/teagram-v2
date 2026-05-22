import typing
import types

from .client import CustomClient
from .database import Database
from .translator import Translator, ModuleTranslator

from importlib.abc import SourceLoader
from abc import ABC, abstractmethod


class ABCLoader(ABC):
    def __init__(self, client: CustomClient, database: Database):
        self.client: CustomClient
        self.database: Database

        self.modules: typing.List[Module]
        self.core_modules: typing.Final[typing.List[str]]

        self.commands: typing.Dict[str, types.FunctionType]
        self.aliases: typing.Dict[str, types.FunctionType]

        self.raw_handlers: typing.List[types.FunctionType]
        self.watchers: typing.List[types.FunctionType]

        self.inline_handlers: typing.Dict[str, types.FunctionType]
        self.callback_handlers: typing.Dict[str, types.FunctionType]

        self.message_handlers: typing.List[types.FunctionType]

        self.dispatcher: typing.Any
        self.inline_dispatcher: typing.Any

        self.translator: Translator

    @abstractmethod
    async def load_module(self, *args, **kwargs):
        pass

    @abstractmethod
    async def unload_module(self, *args, **kwargs):
        pass

    @abstractmethod
    def prepare_module(self, *args, **kwargs):
        pass


class ModuleException(Exception):
    pass


class ModuleVersionException(Exception):
    pass


class Module:
    MIN_VERSION = "BETA"
    MODULE_VERSION = "Not specified"

    translator: ModuleTranslator

    def get(self, key: str) -> typing.Optional[str]:
        return self.translator.get(key)

    def load_init(self):
        self.commands = get_methods(self, "cmd", "is_command")
        self.watchers = get_methods(self, "watcher", "is_watcher")

        self.inline_handlers = get_methods(self, "_inline_handler", "is_inline_handler")
        self.callback_handlers = get_methods(
            self, "_callback_handler", "is_callback_handler"
        )

        self.raw_handlers = get_methods(self, "raw_handler", "is_raw_handler")
        self.message_handlers = list(
            get_methods(self, "_message_handler", "is_message_handler").values()
        )

    async def on_load(self):
        pass

    async def on_unload(self):
        pass


class StringLoader(SourceLoader):
    def __init__(self, data: str, origin: str) -> None:
        self.data = data.encode("utf-8")
        self.origin = origin

    def get_code(self, full_name: str):
        if source := self.get_source(full_name):
            return compile(source, self.origin, "exec", dont_inherit=True)
        else:
            return None

    def get_filename(self, _: str) -> str:
        return self.origin

    def get_data(self, _: str) -> str:
        return self.data


def get_methods(cls, end: str, attribute: str = ""):
    methods = {}

    for method_name in dir(cls):
        method = getattr(cls, method_name)

        if callable(method) and (
            method_name.endswith(end) or hasattr(method, attribute)
        ):
            key = method_name.replace(end, "")
            methods[key] = method

    return methods
