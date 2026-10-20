from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import get_book_actions_keyboard
from app.core.i18n import t
from app.database.repositories.user_repo import UserRepository
from app.services.analysis import BookAnalysisService
from app.services.book_search import BookSearchService
from app.services.favorites import FavoritesService
from app.utils.text import escape_html, format_book_caption, format_book_details

router = Router(name="book_detail")


@router.callback_query(F.data.startswith("book:view:"))
async def handle_book_view(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    parts = callback.data.split(":")
    book_id = int(parts[2])

    search_service = BookSearchService(session)
    fav_service = FavoritesService(session)
    user_repo = UserRepository(session)

    book = await search_service.get_book_by_id(book_id)
    if not book:
        await callback.answer(t(lang, "errors.book_not_found"), show_alert=True)
        return

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    is_fav = False
    if user and book.id:
        is_fav = await fav_service.is_favorite(user.id, book.id)

    caption = format_book_caption(book, lang)
    kb = get_book_actions_keyboard(book_id, is_fav, lang)

    if book.cover_url and callback.message:
        try:
            await callback.message.answer_photo(
                photo=book.cover_url,
                caption=caption,
                reply_markup=kb,
                parse_mode="HTML",
            )
            await callback.answer()
            return
        except Exception:
            # Fallback to text message if photo fails to load
            pass

    if callback.message:
        await callback.message.answer(caption, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("book:details:"))
async def handle_book_details(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    parts = callback.data.split(":")
    book_id = int(parts[2])

    search_service = BookSearchService(session)
    book = await search_service.get_book_by_id(book_id)
    if not book:
        await callback.answer(t(lang, "errors.book_not_found"), show_alert=True)
        return

    text = format_book_details(book, lang)
    if callback.message:
        await callback.message.answer(text, parse_mode="HTML", disable_web_page_preview=False)
    await callback.answer()


@router.callback_query(F.data.startswith("book:ai:"))
async def handle_book_ai(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    parts = callback.data.split(":")
    book_id = int(parts[2])

    search_service = BookSearchService(session)
    book = await search_service.get_book_by_id(book_id)
    if not book:
        await callback.answer(t(lang, "errors.book_not_found"), show_alert=True)
        return

    wait_msg: Message | None = None
    if callback.message:
        wait_msg = await callback.message.answer(t(lang, "ai.loading"))

    ai_service = BookAnalysisService(session)
    analysis = await ai_service.get_or_create_analysis(book, language=lang)

    lines = [
        f"🧠 <b>{escape_html(book.title)} — {t(lang, 'book.btn_ai_analysis')}</b>",
        "",
        f"📌 <b>{t(lang, 'ai.summary_title')}</b>",
        escape_html(analysis.summary),
        "",
    ]

    if analysis.key_ideas:
        lines.append(f"💡 <b>{t(lang, 'ai.key_ideas_title')}</b>")
        for idea in analysis.key_ideas:
            lines.append(f"• {escape_html(idea)}")
        lines.append("")

    if analysis.lessons:
        lines.append(f"🌱 <b>{t(lang, 'ai.lessons_title')}</b>")
        for lesson in analysis.lessons:
            lines.append(f"• {escape_html(lesson)}")
        lines.append("")

    if analysis.target_audience:
        lines.append(f"🎯 <b>{t(lang, 'ai.audience_title')}</b>")
        lines.append(escape_html(analysis.target_audience))
        lines.append("")

    lines.append(t(lang, "ai.disclaimer"))

    response_text = "\n".join(lines)
    if wait_msg:
        await wait_msg.edit_text(response_text, parse_mode="HTML")
    elif callback.message:
        await callback.message.answer(response_text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("book:legal:"))
async def handle_book_legal_sources(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    parts = callback.data.split(":")
    book_id = int(parts[2])

    search_service = BookSearchService(session)
    book = await search_service.get_book_by_id(book_id)
    if not book:
        await callback.answer(t(lang, "errors.book_not_found"), show_alert=True)
        return

    access_label = t(lang, f"book.access_{book.access_type}")
    lines = [
        f"📖 <b>{t(lang, 'book.reading_sources_header')}</b>",
        f"📚 <i>{escape_html(book.title)}</i>",
        "",
        f"<b>Holati / Статус:</b> {access_label}",
    ]

    if book.reading_url:
        lines.append(f"\n🔗 <a href=\"{escape_html(book.reading_url)}\">Manbani ochish / Открыть источник</a>")
    elif book.source_url:
        lines.append(f"\n🔗 <a href=\"{escape_html(book.source_url)}\">Bibliografik sahifa / Страница источника</a>")
    else:
        lines.append("\nTo'g'ridan-to'g'ri elektron havola mavjud emas.")

    if callback.message:
        await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("book:similar:"))
async def handle_book_similar(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    parts = callback.data.split(":")
    book_id = int(parts[2])

    search_service = BookSearchService(session)
    book = await search_service.get_book_by_id(book_id)
    if not book:
        await callback.answer(t(lang, "errors.book_not_found"), show_alert=True)
        return

    # Search similar by author or genre
    author_query = book.authors[0] if book.authors else book.title
    similar_books = await search_service.search(author_query, limit=5)
    filtered = [b for b in similar_books if b.id != book.id]

    lines = [
        f"🔍 <b>'{escape_html(book.title)}' uchun tavsiyalar:</b>",
        "",
    ]
    if filtered:
        for idx, b in enumerate(filtered, 1):
            lines.append(f"{idx}. <b>{escape_html(b.title)}</b> — <i>{escape_html(b.authors_display)}</i>")
    else:
        lines.append(t(lang, "recommendations.empty"))

    if callback.message:
        await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()
