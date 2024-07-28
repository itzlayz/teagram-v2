from importlib.abc import SourceLoader


def get_methods(cls, end: str, attribute: str = ""):
    return {
        method_name.replace(end, ""): getattr(cls, method_name)
        for method_name in dir(cls)
        if callable(getattr(cls, method_name))
        and (method_name.endswith(end) or hasattr(getattr(cls, method_name), attribute))
    }


class ModuleException(Exception):
    pass


class Module:
    MIN_VERSION = "BETA"
    MODULE_VERSION = "Not specified"

    def load_init(self):
        self.commands = get_methods(self, "cmd", "is_command")
        self.watchers = get_methods(self, "watcher", "is_watcher")
        self.inline_handlers = get_methods(self, "inline_handler", "is_inline_handler")
        self.callback_handlers = get_methods(
            self, "callback_handler", "is_callback_handler"
        )
        self.raw_handlers = get_methods(self, "raw_handler", "is_raw_handler")

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
