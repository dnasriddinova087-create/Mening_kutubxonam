import json
from pathlib import Path
from typing import Any

DEFAULT_LOCALE = "uz"
SUPPORTED_LOCALES = ["uz", "ru", "en"]

LANGUAGE_NAMES = {
    "uz": "O'zbekcha 🇺🇿",
    "ru": "Русский 🇷🇺",
    "en": "English 🇬🇧",
}

_TRANSLATIONS: dict[str, dict[str, Any]] = {}


def load_translations(locales_dir: Path | None = None) -> None:
    global _TRANSLATIONS
    if locales_dir is None:
        locales_dir = Path(__file__).resolve().parent.parent.parent / "locales"

    for lang in SUPPORTED_LOCALES:
        file_path = locales_dir / f"{lang}.json"
        if file_path.exists():
            with open(file_path, encoding="utf-8") as f:
                _TRANSLATIONS[lang] = json.load(f)
        else:
            _TRANSLATIONS[lang] = {}


def get_nested(data: dict[str, Any], path: str) -> Any:
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def t(lang: str, key: str, **kwargs) -> str:
    if not _TRANSLATIONS:
        load_translations()

    if lang not in SUPPORTED_LOCALES:
        lang = DEFAULT_LOCALE

    text = get_nested(_TRANSLATIONS.get(lang, {}), key)
    if text is None and lang != DEFAULT_LOCALE:
        # Fallback to default locale
        text = get_nested(_TRANSLATIONS.get(DEFAULT_LOCALE, {}), key)

    if text is None:
        return key

    if not isinstance(text, str):
        return str(text)

    try:
        return text.format(**kwargs)
    except KeyError:
        return text


# Initialize on import
load_translations()
