
from typing import Any

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
            lang_tag = ""
            if b.language:
                l_clean = b.language.lower()
                if l_clean in ("uz", "uzb"):
                    lang_tag = " [UZ]"
                elif l_clean in ("ru", "rus"):
                    lang_tag = " [RU]"
                elif l_clean in ("en", "eng"):
                    lang_tag = " [EN]"
            label = f"📖 {truncate_text(b.title, 24)}{lang_tag}"
            if b.authors:
                label += f" — {truncate_text(b.authors[0], 14)}"
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
    book_or_id: int | BookDTO, is_favorite: bool, lang: str = "uz"
) -> InlineKeyboardMarkup:
    """Action buttons for a single book card with media support."""
    if isinstance(book_or_id, BookDTO):
        book_id = book_or_id.id or 0
        book = book_or_id
    else:
        book_id = book_or_id
        book = None

    fav_text = t(lang, "book.btn_remove_favorite" if is_favorite else "book.btn_add_favorite")

    buttons: list[list[InlineKeyboardButton]] = []

    # Quick external media buttons if available
    media_row: list[InlineKeyboardButton] = []
    if book and book.reading_url:
        media_row.append(InlineKeyboardButton(text="📖 Mutolaa", url=book.reading_url))
    if book and getattr(book, "file_url", None):
        fmt = getattr(book, "file_format", "PDF") or "PDF"
        media_row.append(InlineKeyboardButton(text=f"📥 Yuklab olish ({fmt})", url=book.file_url))
    if media_row:
        buttons.append(media_row)

    av_row: list[InlineKeyboardButton] = []
    if book and getattr(book, "audio_url", None):
        av_row.append(InlineKeyboardButton(text="🎧 Audiokitob", url=book.audio_url))
    if book and getattr(book, "video_url", None):
        av_row.append(InlineKeyboardButton(text="🎬 Video sharh", url=book.video_url))
    if av_row:
        buttons.append(av_row)

    # Core action buttons
    buttons.append([
        InlineKeyboardButton(text=t(lang, "book.btn_details"), callback_data=f"book:details:{book_id}"),
        InlineKeyboardButton(text=t(lang, "book.btn_ai_analysis"), callback_data=f"book:ai:{book_id}"),
    ])
    buttons.append([
        InlineKeyboardButton(text=fav_text, callback_data=f"book:fav:{book_id}"),
        InlineKeyboardButton(text=t(lang, "book.btn_reading_list"), callback_data=f"book:readlist:{book_id}"),
    ])
    buttons.append([
        InlineKeyboardButton(text=t(lang, "book.btn_legal_sources"), callback_data=f"book:legal:{book_id}"),
        InlineKeyboardButton(text=t(lang, "book.btn_similar"), callback_data=f"book:similar:{book_id}"),
    ])
    buttons.append([
        InlineKeyboardButton(text=t(lang, "book.btn_back"), callback_data="search:back"),
    ])
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


def get_language_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Inline keyboard for switching interface language."""
    buttons = [
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton(text=t(lang, "language.book_lang_btn"), callback_data="booklang:menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_book_language_keyboard(
    current_langs: list[str], lang: str = "uz"
) -> InlineKeyboardMarkup:
    """Inline keyboard for configuring preferred book languages in search."""
    uz_check = "✅ " if "uz" in current_langs else ""
    ru_check = "✅ " if "ru" in current_langs else ""
    en_check = "✅ " if "en" in current_langs else ""
    all_check = "✅ " if ("uz" in current_langs and "ru" in current_langs and "en" in current_langs) else ""

    buttons = [
        [InlineKeyboardButton(text=f"{uz_check}🇺🇿 O'zbekcha kitoblar", callback_data="booklang:toggle:uz")],
        [InlineKeyboardButton(text=f"{ru_check}🇷🇺 Русские книги", callback_data="booklang:toggle:ru")],
        [InlineKeyboardButton(text=f"{en_check}🇬🇧 English books", callback_data="booklang:toggle:en")],
        [InlineKeyboardButton(text=f"{all_check}🌍 Barcha tillar / Все языки", callback_data="booklang:toggle:all")],
        [InlineKeyboardButton(text=t(lang, "book.btn_back"), callback_data="lang:menu")],
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


def get_catalog_control_keyboard(
    page: int,
    total_pages: int,
    current_lang: str = "all",
    current_genre: str = "all",
    lang: str = "uz",
) -> InlineKeyboardMarkup:
    """Control and pagination keyboard for full books catalog."""
    buttons: list[list[InlineKeyboardButton]] = []

    # Row 1: Pagination navigation
    nav_row: list[InlineKeyboardButton] = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text=t(lang, "catalog.prev_btn"),
                callback_data=f"cat:page:{page - 1}:{current_lang}:{current_genre}",
            )
        )
    nav_row.append(
        InlineKeyboardButton(
            text=f"📄 {page} / {total_pages}",
            callback_data="noop",
        )
    )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                text=t(lang, "catalog.next_btn"),
                callback_data=f"cat:page:{page + 1}:{current_lang}:{current_genre}",
            )
        )
    if nav_row:
        buttons.append(nav_row)

    # Row 2: Language filters
    lang_row: list[InlineKeyboardButton] = [
        InlineKeyboardButton(
            text=f"{'✅ ' if current_lang == 'all' else ''}{t(lang, 'catalog.filter_all')}",
            callback_data=f"cat:lang:all:{current_genre}",
        ),
        InlineKeyboardButton(
            text=f"{'✅ ' if current_lang == 'uz' else ''}🇺🇿 UZ",
            callback_data=f"cat:lang:uz:{current_genre}",
        ),
        InlineKeyboardButton(
            text=f"{'✅ ' if current_lang == 'ru' else ''}🇷🇺 RU",
            callback_data=f"cat:lang:ru:{current_genre}",
        ),
        InlineKeyboardButton(
            text=f"{'✅ ' if current_lang == 'en' else ''}🇬🇧 EN",
            callback_data=f"cat:lang:en:{current_genre}",
        ),
    ]
    buttons.append(lang_row)

    # Row 3: Genre filters
    genre_row: list[InlineKeyboardButton] = [
        InlineKeyboardButton(
            text=f"{'✅ ' if current_genre == 'all' else ''}🏷️ {t(lang, 'catalog.filter_all')}",
            callback_data=f"cat:genre:all:{current_lang}",
        ),
        InlineKeyboardButton(
            text=f"{'✅ ' if current_genre == 'tarixiy' else ''}Tarixiy",
            callback_data=f"cat:genre:tarixiy:{current_lang}",
        ),
        InlineKeyboardButton(
            text=f"{'✅ ' if current_genre == 'badiiy' else ''}Badiiy / Drama",
            callback_data=f"cat:genre:badiiy:{current_lang}",
        ),
        InlineKeyboardButton(
            text=f"{'✅ ' if current_genre == 'falsafa' else ''}Falsafa",
            callback_data=f"cat:genre:falsafa:{current_lang}",
        ),
    ]
    buttons.append(genre_row)

    # Row 4: Search & Reset
    buttons.append([
        InlineKeyboardButton(text=f"🔍 {t(lang, 'menu.search')}", callback_data="cat:search"),
        InlineKeyboardButton(text=t(lang, "catalog.reset_filters"), callback_data="cat:reset"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_catalog_grid_keyboard(
    books: list[Any],
    page: int,
    total_pages: int,
    lang: str = "uz",
) -> InlineKeyboardMarkup:
    """Generate interactive Grid keyboard matching the serial/movie bot UX in screenshot."""
    buttons: list[list[InlineKeyboardButton]] = []

    # Row 1: Search actions
    buttons.append([
        InlineKeyboardButton(text="🚨 Nomi orqali qidiruv", callback_data="cat:search"),
        InlineKeyboardButton(text="🔍 Kod orqali qidiruv", callback_data="cat:code_prompt"),
    ])

    # Row 2+: Book buttons in 2 columns
    row: list[InlineKeyboardButton] = []
    for b in books:
        code_tag = f"[{b.code}] " if getattr(b, "code", None) else ""
        title = getattr(b, "original_title", getattr(b, "title", "Kitob"))
        label = f"{code_tag}{truncate_text(title, 20)}"
        row.append(InlineKeyboardButton(text=label, callback_data=f"book:view:{b.id}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Navigation row
    nav_row: list[InlineKeyboardButton] = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"cat:grid:{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page} / {total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"cat:grid:{page + 1}"))
    buttons.append(nav_row)

    # Toggle to full cards / reset
    buttons.append([
        InlineKeyboardButton(text="🖼️ Kartochkalar ko'rinishi", callback_data=f"cat:page:{page}:all:all"),
        InlineKeyboardButton(text="🔄 Filtrlarni tozalash", callback_data="cat:reset"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

