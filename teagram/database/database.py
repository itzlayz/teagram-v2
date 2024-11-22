import typing

import ujson
import os


class JSONSerializable:
    pass


class Database:
    def __init__(self, filename="database.json"):
        self.filename = filename
        self._load()

    def _load(self):
        if os.path.exists(self.filename):
            with open(self.filename, "r") as file:
                self.data = ujson.load(file)
        else:
            with open(self.filename, "w") as file:
                ujson.dump(
                    {
                        "teagram": {
                            "prefix": ["."],
                            "inline_token": None,
                        },
                    },
                    file,
                    indent=4,
                )

            self._load()

    def _save(self):
        with open(self.filename, "w") as file:
            ujson.dump(self.data, file, indent=4)

    def get(self, section: str, key: str, default: typing.Any = None) -> typing.Any:
        return self.data.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: JSONSerializable):
        if section not in self.data:
            self.data[section] = {}

        self.data[section][key] = value
        self._save()

    def clear(self):
        self.data = {}
        self._save()

    def pop(self, section: str, key: str, default: typing.Any = None):
        if section in self.data:
            value = self.data[section].pop(key, default)
            if not self.data[section]:
                del self.data[section]

            self._save()
            return value

        return default
