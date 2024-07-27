import ujson
import os


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
                            "aliases": [],
                        },
                    },
                    file,
                    indent=4,
                )

            self._load()

    def _save(self):
        with open(self.filename, "w") as file:
            ujson.dump(self.data, file, indent=4)

    def get(self, section, key, default=None):
        try:
            return self.data[section][key]
        except KeyError:
            return default

    def set(self, section, key, value):
        try:
            self.data[section][key] = value
        except KeyError:
            pass

        self._save()

    def clear(self):
        self.data = {}
        self._save()
