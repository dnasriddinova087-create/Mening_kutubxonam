from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import get_language_keyboard
from app.bot.keyboards.reply import get_main_menu_keyboard
from app.core.i18n import SUPPORTED_LOCALES, t
from app.database.repositories.user_repo import UserRepository

router = Router(name="language")


@router.message(Command("language"))
@router.message(F.text.in_(["🌐 Til", "🌐 Язык", "🌐 Language"]))
async def handle_language_prompt(message: Message, lang: str = "uz"):
    kb = get_language_keyboard()
    await message.answer(t(lang, "language.choose"), reply_markup=kb)


@router.callback_query(F.data.startswith("lang:"))
async def handle_language_select(callback: CallbackQuery, session: AsyncSession):
    new_lang = callback.data.split(":")[1]
    if new_lang not in SUPPORTED_LOCALES:
        new_lang = "uz"

    user_repo = UserRepository(session)
    await user_repo.update_language(callback.from_user.id, new_lang)

    success_msg = t(new_lang, "language.changed")
    reply_kb = get_main_menu_keyboard(new_lang)

    if callback.message:
        await callback.message.answer(success_msg, reply_markup=reply_kb, parse_mode="HTML")
        try:
            await callback.message.delete()
        except Exception:
            pass
    await callback.answer()
