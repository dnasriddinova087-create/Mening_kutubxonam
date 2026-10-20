import math

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import get_catalog_control_keyboard
from app.bot.states.search_state import SearchStates
from app.core.i18n import t
from app.core.logging import logger
from app.database.models import Book
from app.database.repositories.book_repo import BookRepository

router = Router(name="catalog")

CATALOG_MENU_TEXTS = [
    "📚 Barcha kitoblar katalogi",
    "📚 Каталог всех книг",
    "📚 All Books Catalog",
]


def format_book_caption(book: Book, lang: str = "uz") -> str:
    """Format rich, concise caption for a catalog book card under 1024 characters."""
    title = book.original_title or "Nomsiz kitob"
    authors = ", ".join(book.authors) if book.authors else ""
    genres = ", ".join(book.genres[:3]) if book.genres else ""
    lang_code = (book.language or "").upper()
    access = (book.access_type or "info").upper()

    caption_lines = [f"📖 <b>{title}</b>"]
    if authors:
        caption_lines.append(f"✍️ <i>{authors}</i>")

    meta_parts = []
    if lang_code:
        meta_parts.append(f"🌐 {lang_code}")
    if genres:
        meta_parts.append(f"🏷️ {genres}")
    if access:
        meta_parts.append(f"⚡ {access}")
    if meta_parts:
        caption_lines.append(" • ".join(meta_parts))

    if book.description:
        desc_clean = book.description.replace("\n", " ").strip()
        snippet = desc_clean[:180] + ("..." if len(desc_clean) > 180 else "")
        caption_lines.append(f"\n{snippet}")

    caption = "\n".join(caption_lines)
    if len(caption) > 1020:
        caption = caption[:1015] + "..."
    return caption


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
        caption = format_book_caption(book, lang)
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
    """Handle opening all books catalog from main menu or /catalog command."""
    wait_msg = await message.answer(f"📚 {t(lang, 'catalog.title')}...")
    await render_and_send_catalog(
        message=message,
        session=session,
        lang=lang,
        page=1,
        lang_filter="all",
        genre_filter="all",
    )
    try:
        await wait_msg.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("cat:page:"))
async def cb_catalog_page(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    """Handle pagination within catalog."""
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
    """Reset all active catalog filters."""
    await callback.answer()
    if callback.message:
        await render_and_send_catalog(
            message=callback.message,
            session=session,
            lang=lang,
            page=1,
            lang_filter="all",
            genre_filter="all",
        )


@router.callback_query(F.data == "cat:search")
async def cb_catalog_search(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    """Quick jump to search from catalog control panel."""
    await callback.answer()
    await state.set_state(SearchStates.waiting_for_query)
    prompt_text = t(lang, "search.prompt")
    if callback.message:
        await callback.message.answer(prompt_text)
