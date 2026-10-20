from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.core.i18n import t


def get_main_menu_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Generate persistent main reply keyboard localized to the user's language."""
    kb = [
        [
            KeyboardButton(text=t(lang, "menu.search")),
            KeyboardButton(text=t(lang, "menu.catalog")),
        ],
        [
            KeyboardButton(text=t(lang, "menu.recommend")),
            KeyboardButton(text=t(lang, "menu.favorites")),
        ],
        [
            KeyboardButton(text=t(lang, "menu.reading_list")),
            KeyboardButton(text=t(lang, "menu.stats")),
        ],
        [
            KeyboardButton(text=t(lang, "menu.language")),
            KeyboardButton(text=t(lang, "menu.help")),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, is_persistent=True)
