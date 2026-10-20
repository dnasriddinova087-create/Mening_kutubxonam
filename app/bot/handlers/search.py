import uuid

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import get_search_results_keyboard
from app.bot.states.search_state import SearchStates
from app.core.i18n import t
from app.schemas.book import BookDTO
from app.services.book_search import BookSearchService
from app.services.user_service import UserService
from app.utils.pagination import paginate

router = Router(name="search")

# Temporary cache for search results by search_id
_SEARCH_CACHE: dict[str, list[BookDTO]] = {}


@router.message(Command("search"))
@router.message(F.text.in_(["🔎 Kitob qidirish", "🔎 Поиск книг", "🔎 Search Books"]))
async def cmd_search_prompt(message: Message, state: FSMContext, lang: str = "uz"):
    await state.set_state(SearchStates.waiting_for_query)
    prompt_text = t(lang, "search.prompt")
    await message.answer(prompt_text)


@router.callback_query(F.data == "search:back")
async def cb_back_to_search_results(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    data = await state.get_data()
    search_id = data.get("current_search_id")
    page = data.get("current_page", 1)

    if search_id and search_id in _SEARCH_CACHE:
        books = _SEARCH_CACHE[search_id]
        paged = paginate(books, page=page, per_page=5)
        header = t(
            lang,
            "search.results_header",
            query=data.get("query", ""),
            page=paged.page,
            total_pages=paged.total_pages,
        )
        kb = get_search_results_keyboard(paged.items, paged.page, paged.total_pages, search_id, lang)
        if callback.message:
            await callback.message.answer(header, reply_markup=kb, parse_mode="HTML")
            try:
                await callback.message.delete()
            except Exception:
                pass
    await callback.answer()


@router.callback_query(F.data.startswith("page:"))
async def handle_pagination_callback(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer(t(lang, "errors.stale_callback"))
        return

    search_id = parts[1]
    target_page = int(parts[2])

    if search_id not in _SEARCH_CACHE:
        await callback.answer(t(lang, "errors.stale_callback"), show_alert=True)
        return

    books = _SEARCH_CACHE[search_id]
    paged = paginate(books, page=target_page, per_page=5)

    data = await state.get_data()
    query = data.get("query", "")
    await state.update_data(current_page=paged.page)

    header = t(
        lang,
        "search.results_header",
        query=query,
        page=paged.page,
        total_pages=paged.total_pages,
    )
    kb = get_search_results_keyboard(paged.items, paged.page, paged.total_pages, search_id, lang)

    if callback.message:
        await callback.message.edit_text(header, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "noop")
async def handle_noop_callback(callback: CallbackQuery):
    await callback.answer()


@router.message(SearchStates.waiting_for_query)
@router.message(F.text & ~F.text.startswith("/"))
async def handle_search_query(
    message: Message, state: FSMContext, session: AsyncSession, lang: str = "uz"
):
    query = message.text.strip()
    if not query:
        return

    # Check if user clicked any main menu button by mistake
    menu_texts = [
        "🔎 Kitob qidirish", "🔎 Поиск книг", "🔎 Search Books",
        "✨ Kitob tavsiya qilish", "✨ Рекомендации", "✨ Recommendations",
        "🔖 Sevimli kitoblarim", "🔖 Мои избранные", "🔖 My Favorites",
        "📚 O‘qish ro‘yxatim", "📚 Список чтения", "📚 Reading List",
        "📊 Statistikam", "📊 Моя статистика", "📊 My Statistics",
        "🌐 Til", "🌐 Язык", "🌐 Language",
        "ℹ️ Yordam", "ℹ️ Помощь", "ℹ️ Help",
    ]
    if query in menu_texts:
        return

    wait_msg = await message.answer(t(lang, "search.searching"))

    search_service = BookSearchService(session)
    user_service = UserService(session)

    results = await search_service.search(query, limit=15)

    # Log search in history
    if message.from_user:
        await user_service.log_search(message.from_user.id, query, len(results))

    await state.clear()

    if not results:
        no_res_text = t(lang, "search.no_results", query=query)
        await wait_msg.edit_text(no_res_text, parse_mode="HTML")
        return

    # Cache results
    search_id = uuid.uuid4().hex[:10]
    _SEARCH_CACHE[search_id] = results
    await state.update_data(current_search_id=search_id, query=query, current_page=1)

    paged = paginate(results, page=1, per_page=5)
    header = t(
        lang,
        "search.results_header",
        query=query,
        page=paged.page,
        total_pages=paged.total_pages,
    )
    kb = get_search_results_keyboard(paged.items, paged.page, paged.total_pages, search_id, lang)

    await wait_msg.edit_text(header, reply_markup=kb, parse_mode="HTML")
