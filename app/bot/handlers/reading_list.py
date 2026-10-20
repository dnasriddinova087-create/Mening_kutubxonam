from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import get_reading_status_keyboard
from app.core.i18n import t
from app.database.repositories.user_repo import UserRepository
from app.services.reading_list import ReadingListService

router = Router(name="reading_list")


@router.message(F.text.in_(["📚 O‘qish ro‘yxatim", "📚 Список чтения", "📚 Reading List"]))
async def handle_view_reading_list(message: Message, session: AsyncSession, lang: str = "uz"):
    user_repo = UserRepository(session)
    reading_service = ReadingListService(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer(t(lang, "reading_list.empty"))
        return

    items = await reading_service.get_items(user.id, limit=30)
    if not items:
        await message.answer(t(lang, "reading_list.empty"))
        return

    buttons = []
    for status, b in items:
        if b.id:
            status_emoji = "⏳" if status == "want_to_read" else ("📖" if status == "reading" else "✅")
            label = f"{status_emoji} {b.title}"
            buttons.append([InlineKeyboardButton(text=label[:45], callback_data=f"book:view:{b.id}")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(t(lang, "reading_list.title"), reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("book:readlist:"))
async def handle_show_reading_status_picker(
    callback: CallbackQuery, session: AsyncSession, lang: str = "uz"
):
    parts = callback.data.split(":")
    book_id = int(parts[2])

    kb = get_reading_status_keyboard(book_id, lang)
    if callback.message:
        await callback.message.answer(t(lang, "reading_list.select_status"), reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("read:set:"))
async def handle_set_reading_status(
    callback: CallbackQuery, session: AsyncSession, lang: str = "uz"
):
    parts = callback.data.split(":")
    status = parts[2]
    book_id = int(parts[3])

    user_repo = UserRepository(session)
    reading_service = ReadingListService(session)

    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer(t(lang, "errors.general"), show_alert=True)
        return

    await reading_service.update_status(user.id, book_id, status)
    status_label = t(lang, f"reading_list.{status}")
    msg = t(lang, "reading_list.status_updated", status=status_label)
    await callback.answer(msg, show_alert=True)
