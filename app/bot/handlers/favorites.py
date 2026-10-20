from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import get_book_actions_keyboard
from app.core.i18n import t
from app.database.repositories.user_repo import UserRepository
from app.services.favorites import FavoritesService

router = Router(name="favorites")


@router.message(Command("favorites"))
@router.message(F.text.in_(["🔖 Sevimli kitoblarim", "🔖 Мои избранные", "🔖 My Favorites"]))
async def handle_list_favorites(message: Message, session: AsyncSession, lang: str = "uz"):
    user_repo = UserRepository(session)
    fav_service = FavoritesService(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer(t(lang, "favorites.empty"))
        return

    fav_books = await fav_service.get_favorites(user.id, offset=0, limit=20)
    if not fav_books:
        await message.answer(t(lang, "favorites.empty"))
        return

    buttons = []
    for b in fav_books:
        if b.id:
            label = f"🔖 {b.title} ({b.authors_display})"
            buttons.append([InlineKeyboardButton(text=label[:45], callback_data=f"book:view:{b.id}")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(t(lang, "favorites.title"), reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("book:fav:"))
async def handle_toggle_favorite(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    parts = callback.data.split(":")
    book_id = int(parts[2])

    user_repo = UserRepository(session)
    fav_service = FavoritesService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer(t(lang, "errors.general"), show_alert=True)
        return

    is_added = await fav_service.toggle_favorite(user.id, book_id)

    alert_msg = t(lang, "favorites.added") if is_added else t(lang, "favorites.removed")
    await callback.answer(alert_msg, show_alert=False)

    # Refresh buttons on the message
    new_kb = get_book_actions_keyboard(book_id, is_added, lang)
    try:
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=new_kb)
    except Exception:
        pass
