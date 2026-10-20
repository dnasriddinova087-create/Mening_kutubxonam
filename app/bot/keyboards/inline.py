
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.i18n import t
from app.schemas.book import BookDTO
from app.utils.text import truncate_text


def get_search_results_keyboard(
    books: list[BookDTO], page: int, total_pages: int, search_id: str, lang: str = "uz"
) -> InlineKeyboardMarkup:
    """Keyboard for paginated search results."""
    buttons: list[list[InlineKeyboardButton]] = []

    # Book items
    for b in books:
        if b.id:
            label = f"📖 {truncate_text(b.title, 28)}"
            if b.authors:
                label += f" — {truncate_text(b.authors[0], 16)}"
            cb_data = f"book:view:{b.id}"
            buttons.append([InlineKeyboardButton(text=label, callback_data=cb_data)])

    # Pagination navigation row
    nav_row: list[InlineKeyboardButton] = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text=t(lang, "search.prev_btn"),
                callback_data=f"page:{search_id}:{page - 1}",
            )
        )
    nav_row.append(
        InlineKeyboardButton(
            text=f"{page} / {total_pages}",
            callback_data="noop",
        )
    )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                text=t(lang, "search.next_btn"),
                callback_data=f"page:{search_id}:{page + 1}",
            )
        )
    if nav_row:
        buttons.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_book_actions_keyboard(
    book_id: int, is_favorite: bool, lang: str = "uz"
) -> InlineKeyboardMarkup:
    """Action buttons for a single book card."""
    fav_text = t(lang, "book.btn_remove_favorite" if is_favorite else "book.btn_add_favorite")

    buttons = [
        [
            InlineKeyboardButton(text=t(lang, "book.btn_details"), callback_data=f"book:details:{book_id}"),
            InlineKeyboardButton(text=t(lang, "book.btn_ai_analysis"), callback_data=f"book:ai:{book_id}"),
        ],
        [
            InlineKeyboardButton(text=fav_text, callback_data=f"book:fav:{book_id}"),
            InlineKeyboardButton(text=t(lang, "book.btn_reading_list"), callback_data=f"book:readlist:{book_id}"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "book.btn_legal_sources"), callback_data=f"book:legal:{book_id}"),
            InlineKeyboardButton(text=t(lang, "book.btn_similar"), callback_data=f"book:similar:{book_id}"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "book.btn_back"), callback_data="search:back"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_reading_status_keyboard(book_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    """Keyboard for selecting reading status."""
    buttons = [
        [
            InlineKeyboardButton(
                text=t(lang, "reading_list.want_to_read"),
                callback_data=f"read:set:want_to_read:{book_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=t(lang, "reading_list.reading"),
                callback_data=f"read:set:reading:{book_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=t(lang, "reading_list.finished"),
                callback_data=f"read:set:finished:{book_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=t(lang, "book.btn_back"),
                callback_data=f"book:view:{book_id}",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for switching languages."""
    buttons = [
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_profile_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Inline keyboard for profile actions."""
    buttons = [
        [
            InlineKeyboardButton(
                text=t(lang, "profile.btn_set_goal"), callback_data="profile:set_goal"
            )
        ],
        [
            InlineKeyboardButton(
                text=t(lang, "profile.btn_export"), callback_data="profile:export"
            )
        ],
        [
            InlineKeyboardButton(
                text=t(lang, "profile.btn_delete_account"),
                callback_data="profile:delete_confirm",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_delete_confirm_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Confirmation for GDPR data deletion."""
    buttons = [
        [
            InlineKeyboardButton(
                text="⚠️ Ha, o'chirish / Да, удалить / Yes, delete",
                callback_data="profile:delete_execute",
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Bekor qilish / Отмена / Cancel", callback_data="profile:view"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
