from os import listdir
import yaml
import typing

SUPPORTED_LANGUAGES = [
    lang[:-5] for lang in listdir("teagram/translations") if lang.endswith(".yaml")
]


class Translator:
    def __init__(self, database):
        self.database = database
        self.translations: typing.Dict[str, typing.Dict[str, str]] = {}

        self.fetch_translations()

    @property
    def language(self) -> str:
        lang = self.database.get("teagram", "language")
        if not lang:
            lang = "en"
            self.database.set("teagram", "language", lang)
        return lang

    @language.setter
    def language(self, lang: str) -> None:
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Invalid language. Supported languages: {', '.join(SUPPORTED_LANGUAGES)}"
            )
        if self.language != lang:
            self.database.set("teagram", "language", lang)
            self.fetch_translations()

    def fetch_translations(self) -> None:
        try:
            with open(
                f"teagram/translations/{self.language}.yaml", encoding="utf-8"
            ) as stream:
                self.translations = yaml.safe_load(stream) or {}
        except FileNotFoundError:
            self.translations = {}

    def __getitem__(self, section: str, key: str) -> typing.Optional[str]:
        return self.translations.get(section, {}).get(key)

    def get(self, section: str, key: str) -> typing.Optional[str]:
        return self.__getitem__(section, key)


class ModuleTranslator:
    def __init__(
        self,
        module_class,
        translator: "Translator",
        module_translations: typing.Optional[typing.Dict[str, str]] = None,
    ):
        self.module_name = (
            module_class.__class__.__name__.lower()
            .replace("mod", "")
            .replace("module", "")
        )

        self.module_translations = module_translations or {}
        if not translator.translations.get(self.module_name):
            self.module_name = self.module_translations.get(
                "name", self.module_name
            ).lower()

        self.translator = translator

    def __getitem__(self, key: str) -> typing.Optional[str]:
        translations = self.translator.translations.get(
            self.module_name, self.module_translations
        )
        return translations.get(key) if translations else None

    def get(self, key: str) -> typing.Optional[str]:
        return self[key]
