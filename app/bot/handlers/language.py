from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import get_book_language_keyboard, get_language_keyboard
from app.bot.keyboards.reply import get_main_menu_keyboard
from app.core.i18n import SUPPORTED_LOCALES, t
from app.database.repositories.user_repo import UserRepository

router = Router(name="language")


@router.message(Command("language"))
@router.message(F.text.in_(["🌐 Til", "🌐 Язык", "🌐 Language"]))
async def handle_language_prompt(message: Message, lang: str = "uz"):
    kb = get_language_keyboard(lang)
    await message.answer(t(lang, "language.choose"), reply_markup=kb)


@router.callback_query(F.data == "lang:menu")
async def handle_language_menu_cb(callback: CallbackQuery, lang: str = "uz"):
    kb = get_language_keyboard(lang)
    if callback.message:
        await callback.message.edit_text(t(lang, "language.choose"), reply_markup=kb)
    await callback.answer()


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
    await callback.answer(success_msg)


@router.callback_query(F.data == "booklang:menu")
async def handle_book_lang_menu(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    current_langs = (user.preferred_book_languages if user and user.preferred_book_languages else [lang])

    kb = get_book_language_keyboard(current_langs, lang)
    if callback.message:
        await callback.message.edit_text(t(lang, "language.book_lang_choose"), reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("booklang:toggle:"))
async def handle_book_lang_toggle(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    target = callback.data.split(":")[2]
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    current = list(user.preferred_book_languages or []) if user else [lang]

    if target == "all":
        current = ["uz", "ru", "en"]
    elif target in current:
        if len(current) > 1:
            current.remove(target)
    else:
        current.append(target)

    await user_repo.update_preferred_book_languages(callback.from_user.id, current)

    kb = get_book_language_keyboard(current, lang)
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=kb)

    langs_display = ", ".join(current).upper()
    await callback.answer(t(lang, "language.book_lang_changed", langs=langs_display))
