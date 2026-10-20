import math
import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import (
    get_book_actions_keyboard,
    get_catalog_control_keyboard,
    get_catalog_grid_keyboard,
)
from app.bot.states.search_state import SearchStates
from app.core.i18n import t
from app.core.logging import logger
from app.database.models import Book
from app.database.repositories.book_repo import BookRepository, book_to_dto
from app.database.repositories.user_repo import UserRepository
from app.schemas.book import BookDTO
from app.services.favorites import FavoritesService
from app.utils.text import escape_html

router = Router(name="catalog")

CATALOG_MENU_TEXTS = [
    "📚 Barcha kitoblar katalogi",
    "📚 Каталог всех книг",
    "📚 All Books Catalog",
]


class CatalogStates(StatesGroup):
    waiting_for_book_code = State()


def format_catalog_card_caption(book: Book | BookDTO, lang: str = "uz") -> str:
    """Format rich, concise caption for a catalog book card under 1024 characters."""
    title = getattr(book, "original_title", getattr(book, "title", "Nomsiz kitob"))
    authors = ", ".join(book.authors) if book.authors else ""
    genres = ", ".join(book.genres[:3]) if book.genres else ""
    lang_code = (book.language or "").upper()
    access = (book.access_type or "info").upper()
    code = getattr(book, "code", None)

    code_str = f" [#{code}]" if code else ""
    caption_lines = [f"📖 <b>{escape_html(title)}</b>{code_str}"]
    if authors:
        caption_lines.append(f"✍️ <i>{escape_html(authors)}</i>")

    meta_parts = []
    if code:
        meta_parts.append(f"🆔 Kod: <b>#{code}</b>")
    if lang_code:
        meta_parts.append(f"🌐 {lang_code}")
    if genres:
        meta_parts.append(f"🏷️ {escape_html(genres)}")
    if access:
        meta_parts.append(f"⚡ {access}")
    if meta_parts:
        caption_lines.append(" • ".join(meta_parts))

    # Media availability badges
    media_badges = []
    if getattr(book, "audio_url", None):
        media_badges.append("🎧 Audiokitob")
    if getattr(book, "video_url", None):
        media_badges.append("🎬 Video sharh")
    if getattr(book, "file_url", None):
        fmt = getattr(book, "file_format", "PDF") or "PDF"
        media_badges.append(f"📥 {fmt}")
    if media_badges:
        caption_lines.append("⚡ " + " • ".join(media_badges))

    if book.description:
        desc_clean = book.description.replace("\n", " ").strip()
        snippet = desc_clean[:220] + ("..." if len(desc_clean) > 220 else "")
        caption_lines.append(f"\n{escape_html(snippet)}")

    caption = "\n".join(caption_lines)
    if len(caption) > 1020:
        caption = caption[:1015] + "..."
    return caption


# Alias for backward compatibility
format_book_caption = format_catalog_card_caption


async def send_single_book_card(
    message: Message,
    book: Book,
    session: AsyncSession,
    lang: str = "uz",
) -> None:
    """Send complete, rich visual card for a specific book with all actions."""
    dto = book_to_dto(book)
    user_repo = UserRepository(session)
    fav_service = FavoritesService(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id) if message.from_user else None
    is_fav = False
    if user and book.id:
        is_fav = await fav_service.is_favorite(user.id, book.id)

    caption = format_catalog_card_caption(book, lang)
    kb = get_book_actions_keyboard(dto, is_fav, lang)

    if book.cover_url and (book.cover_url.startswith("http://") or book.cover_url.startswith("https://")):
        try:
            await message.answer_photo(
                photo=book.cover_url,
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb,
            )
            return
        except Exception as e:
            logger.debug(f"Failed to send cover photo: {e}")

    no_cover_tag = t(lang, "catalog.no_cover")
    text_card = f"🖼️ <i>[{no_cover_tag}]</i>\n\n{caption}"
    await message.answer(text_card, parse_mode="HTML", reply_markup=kb)


async def render_and_send_grid_catalog(
    message: Message,
    session: AsyncSession,
    lang: str = "uz",
    page: int = 1,
    per_page: int = 10,
) -> None:
    """Display interactive grid of book buttons matching movie/serial bot style."""
    repo = BookRepository(session)
    offset = (page - 1) * per_page
    books, total_count = await repo.list_books(
        offset=offset,
        limit=per_page,
        include_archived=False,
    )

    total_pages = max(1, math.ceil(total_count / per_page)) if total_count > 0 else 1

    if not books:
        empty_text = t(lang, "catalog.empty")
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔍 Qidiruv", callback_data="cat:search")]]
        )
        await message.answer(empty_text, parse_mode="HTML", reply_markup=kb)
        return

    text = (
        "📚 <b>Kitoblar ro'yxati</b>\n\n"
        "📌 Kerakli kitobni tanlash uchun uning ustiga bosing yoki qidiruv kodini yuboring (masalan: <code>1</code>, <code>2</code>) ❗️\n\n"
        f"📊 Jami kitoblar soni: <b>{total_count}</b> ta"
    )

    kb = get_catalog_grid_keyboard(books=books, page=page, total_pages=total_pages, lang=lang)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


async def render_and_send_catalog(
    message: Message,
    session: AsyncSession,
    lang: str = "uz",
    page: int = 1,
    lang_filter: str = "all",
    genre_filter: str = "all",
    per_page: int = 5,
) -> None:
    """Fetch books from database, send visual cards with covers, and show pagination controls."""
    repo = BookRepository(session)
    offset = (page - 1) * per_page

    db_lang = None if lang_filter == "all" else lang_filter
    db_genre = None if genre_filter == "all" else genre_filter

    books, total_count = await repo.list_books(
        offset=offset,
        limit=per_page,
        include_archived=False,
        language=db_lang,
        genre=db_genre,
    )

    total_pages = max(1, math.ceil(total_count / per_page)) if total_count > 0 else 1

    if not books:
        empty_text = t(lang, "catalog.empty")
        control_kb = get_catalog_control_keyboard(
            page=1,
            total_pages=1,
            current_lang=lang_filter,
            current_genre=genre_filter,
            lang=lang,
        )
        await message.answer(empty_text, parse_mode="HTML", reply_markup=control_kb)
        return

    open_book_label = t(lang, "catalog.open_book")

    # Send each book card with its cover and dedicated action button
    for book in books:
        caption = format_catalog_card_caption(book, lang)
        book_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=open_book_label, callback_data=f"book:view:{book.id}")]
            ]
        )

        sent_photo = False
        if book.cover_url and (book.cover_url.startswith("http://") or book.cover_url.startswith("https://")):
            try:
                await message.answer_photo(
                    photo=book.cover_url,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=book_kb,
                )
                sent_photo = True
            except Exception as e:
                logger.debug(f"Could not send photo for book {book.id}: {e}")

        if not sent_photo:
            no_cover_tag = t(lang, "catalog.no_cover")
            text_card = f"🖼️ <i>[{no_cover_tag}]</i>\n\n{caption}"
            await message.answer(text_card, parse_mode="HTML", reply_markup=book_kb)

    # Filter description text for header
    filter_parts = []
    if lang_filter != "all":
        filter_parts.append(f"🌐 Til: {lang_filter.upper()}")
    if genre_filter != "all":
        filter_parts.append(f"🏷️ Janr: {genre_filter.capitalize()}")
    filter_desc = " • ".join(filter_parts) if filter_parts else ""

    control_text = t(
        lang,
        "catalog.page_header",
        page=page,
        total_pages=total_pages,
        total_books=total_count,
        filter_desc=f"\n🔍 <b>Faol filtrlar:</b> {filter_desc}" if filter_desc else "",
    )

    control_kb = get_catalog_control_keyboard(
        page=page,
        total_pages=total_pages,
        current_lang=lang_filter,
        current_genre=genre_filter,
        lang=lang,
    )

    await message.answer(control_text, parse_mode="HTML", reply_markup=control_kb)


@router.message(Command("catalog"))
@router.message(F.text.in_(CATALOG_MENU_TEXTS))
async def cmd_open_catalog(message: Message, session: AsyncSession, lang: str = "uz"):
    """Handle opening all books catalog in Grid layout matching user reference screenshot."""
    await render_and_send_grid_catalog(
        message=message,
        session=session,
        lang=lang,
        page=1,
    )


@router.callback_query(F.data.startswith("cat:grid:"))
async def cb_catalog_grid_page(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    """Handle pagination within the grid catalog."""
    target_page = int(callback.data.split(":")[2])
    await callback.answer()
    if callback.message:
        await render_and_send_grid_catalog(
            message=callback.message,
            session=session,
            lang=lang,
            page=target_page,
        )


@router.callback_query(F.data.startswith("cat:page:"))
async def cb_catalog_page(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    """Handle pagination within visual photo cards catalog."""
    parts = callback.data.split(":")
    if len(parts) >= 5:
        target_page = int(parts[2])
        lang_filter = parts[3]
        genre_filter = parts[4]
    else:
        target_page = 1
        lang_filter = "all"
        genre_filter = "all"

    await callback.answer()
    if callback.message:
        await render_and_send_catalog(
            message=callback.message,
            session=session,
            lang=lang,
            page=target_page,
            lang_filter=lang_filter,
            genre_filter=genre_filter,
        )


@router.callback_query(F.data.startswith("cat:lang:"))
async def cb_catalog_filter_lang(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    """Filter catalog by language."""
    parts = callback.data.split(":")
    lang_filter = parts[2] if len(parts) > 2 else "all"
    genre_filter = parts[3] if len(parts) > 3 else "all"

    await callback.answer()
    if callback.message:
        await render_and_send_catalog(
            message=callback.message,
            session=session,
            lang=lang,
            page=1,
            lang_filter=lang_filter,
            genre_filter=genre_filter,
        )


@router.callback_query(F.data.startswith("cat:genre:"))
async def cb_catalog_filter_genre(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    """Filter catalog by genre."""
    parts = callback.data.split(":")
    genre_filter = parts[2] if len(parts) > 2 else "all"
    lang_filter = parts[3] if len(parts) > 3 else "all"

    await callback.answer()
    if callback.message:
        await render_and_send_catalog(
            message=callback.message,
            session=session,
            lang=lang,
            page=1,
            lang_filter=lang_filter,
            genre_filter=genre_filter,
        )


@router.callback_query(F.data == "cat:reset")
async def cb_catalog_reset(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    """Reset all active catalog filters and return to grid."""
    await callback.answer()
    if callback.message:
        await render_and_send_grid_catalog(
            message=callback.message,
            session=session,
            lang=lang,
            page=1,
        )


@router.callback_query(F.data == "cat:code_prompt")
async def cb_catalog_code_prompt(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    """Prompt user to input book code."""
    await callback.answer()
    await state.set_state(CatalogStates.waiting_for_book_code)
    prompt_text = (
        "🔍 <b>KOD ORQALI QIDIRUV</b>\n\n"
        "Kitob qidiruv kodini yuboring (masalan: <code>1</code>, <code>2</code>, <code>5</code>, <code>10</code>):\n\n"
        "<i>Bekor qilish uchun /cancel yuboring.</i>"
    )
    if callback.message:
        await callback.message.answer(prompt_text, parse_mode="HTML")


@router.callback_query(F.data == "cat:search")
async def cb_catalog_search(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    """Quick jump to search from catalog control panel."""
    await callback.answer()
    await state.set_state(SearchStates.waiting_for_query)
    prompt_text = t(lang, "search.prompt")
    if callback.message:
        await callback.message.answer(prompt_text)


@router.message(CatalogStates.waiting_for_book_code)
async def process_book_code_search(
    message: Message, state: FSMContext, session: AsyncSession, lang: str = "uz"
):
    """Handle code entered during waiting_for_book_code state."""
    raw_text = (message.text or "").strip()
    digits = re.findall(r"\d+", raw_text)
    if not digits:
        await message.answer("Iltimos, kitob kodini raqam ko'rinishida kiriting (masalan: 1, 2, 5):")
        return

    await state.clear()
    code = int(digits[0])
    repo = BookRepository(session)
    book = await repo.get_by_code(code)
    if book:
        await send_single_book_card(message=message, book=book, session=session, lang=lang)
    else:
        await message.answer(
            f"❌ <b>#{code}</b> raqamli kitob topilmadi.\n\n"
            "Mavjud barcha kitoblarni ko'rish uchun 📚 <b>Barcha kitoblar katalogi</b> tugmasini bosing.",
            parse_mode="HTML",
        )


@router.message(F.text.regexp(r"^(?:#|kod\s*|kod:\s*|\[#?)(\d+)(?:\])?$"))
@router.message(F.text.regexp(r"^(\d+)$"))
async def handle_direct_code_message(
    message: Message, session: AsyncSession, lang: str = "uz"
):
    """Automatically resolve direct number/code messages (e.g. '1', '#1', 'kod 1') to book cards."""
    text = message.text.strip().lower()
    digits = re.findall(r"\d+", text)
    if not digits:
        return

    code = int(digits[0])
    repo = BookRepository(session)
    book = await repo.get_by_code(code)
    if book:
        await send_single_book_card(message=message, book=book, session=session, lang=lang)
    else:
        # Only answer if explicitly specified as code (starts with '#' or 'kod')
        if text.startswith("#") or "kod" in text:
            await message.answer(
                f"❌ <b>#{code}</b> raqamli kitob bazada topilmadi.\n"
                "Katalogdagi barcha kitoblarni ko'rish uchun 📚 <b>Barcha kitoblar katalogi</b> bo'limini oching.",
                parse_mode="HTML",
            )
