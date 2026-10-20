from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from app.bot.states.user_state import UserStates
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import get_delete_confirm_keyboard, get_profile_keyboard
from app.core.i18n import LANGUAGE_NAMES, t
from app.database.repositories.user_repo import UserRepository
from app.services.user_service import UserService
from app.utils.text import escape_html

router = Router(name="profile")


@router.message(Command("profile"))
@router.message(F.text.in_(["📊 Statistikam", "📊 Моя статистика", "📊 My Statistics"]))
async def handle_profile_view(message: Message, session: AsyncSession, lang: str = "uz"):
    user_service = UserService(session)
    summary = await user_service.get_profile_summary(message.from_user.id)
    if not summary:
        await message.answer(t(lang, "errors.general"))
        return

    user = summary["user"]
    lang_display = LANGUAGE_NAMES.get(user.language, user.language)

    lines = [
        t(lang, "profile.title"),
        "",
        t(lang, "profile.id", id=user.telegram_id),
        t(lang, "profile.name", name=escape_html(user.full_name or "Kitobxon")),
        t(lang, "profile.language", language=lang_display),
        "",
        t(lang, "profile.favorites_count", count=summary["favorites_count"]),
        t(lang, "profile.reading_count", count=summary["reading"]),
        t(lang, "profile.finished_count", count=summary["finished"]),
        t(lang, "profile.searches_count", count=summary["searches_count"]),
        "",
        t(lang, "profile.goal", goal=summary["reading_goal"]),
    ]

    kb = get_profile_keyboard(lang)
    await message.answer("\n".join(lines), reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "profile:view")
async def cb_profile_view(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    user_service = UserService(session)
    summary = await user_service.get_profile_summary(callback.from_user.id)
    if not summary:
        await callback.answer(t(lang, "errors.general"))
        return

    user = summary["user"]
    lang_display = LANGUAGE_NAMES.get(user.language, user.language)

    lines = [
        t(lang, "profile.title"),
        "",
        t(lang, "profile.id", id=user.telegram_id),
        t(lang, "profile.name", name=escape_html(user.full_name or "Kitobxon")),
        t(lang, "profile.language", language=lang_display),
        "",
        t(lang, "profile.favorites_count", count=summary["favorites_count"]),
        t(lang, "profile.reading_count", count=summary["reading"]),
        t(lang, "profile.finished_count", count=summary["finished"]),
        t(lang, "profile.searches_count", count=summary["searches_count"]),
        "",
        t(lang, "profile.goal", goal=summary["reading_goal"]),
    ]

    kb = get_profile_keyboard(lang)
    if callback.message:
        await callback.message.edit_text("\n".join(lines), reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "profile:set_goal")
async def cb_set_goal_prompt(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    await state.set_state(UserStates.setting_goal)
    prompt = "🎯 Oylik o'qish maqsadingizni son bilan kiriting (masalan: 3, 5, 10):"
    if lang == "ru":
        prompt = "🎯 Введите вашу цель по книгам на месяц (например: 3, 5, 10):"
    elif lang == "en":
        prompt = "🎯 Enter your monthly reading goal as a number (e.g. 3, 5, 10):"

    if callback.message:
        await callback.message.answer(prompt)
    await callback.answer()


@router.message(UserStates.setting_goal)
async def handle_set_goal_input(
    message: Message, state: FSMContext, session: AsyncSession, lang: str = "uz"
):
    text = message.text.strip()
    try:
        goal = int(text)
        if goal < 1 or goal > 100:
            raise ValueError()
    except ValueError:
        await message.answer("Iltimos, 1 dan 100 gacha bo'lgan butun son kiriting.")
        return

    user_repo = UserRepository(session)
    await user_repo.update_reading_goal(message.from_user.id, goal)
    await state.clear()

    success_msg = f"✅ Oylik maqsad belgilandi: {goal} ta kitob!"
    if lang == "ru":
        success_msg = f"✅ Цель на месяц установлена: {goal} книг(и)!"
    elif lang == "en":
        success_msg = f"✅ Monthly reading goal set to {goal} books!"

    await message.answer(success_msg)


@router.callback_query(F.data == "profile:export")
async def cb_export_data(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    user_service = UserService(session)
    json_data = await user_service.export_data(callback.from_user.id)

    input_file = BufferedInputFile(
        file=json_data.encode("utf-8"),
        filename=f"kitobxon_export_{callback.from_user.id}.json",
    )
    if callback.message:
        await callback.message.answer_document(
            document=input_file,
            caption=t(lang, "profile.export_caption"),
        )
    await callback.answer()


@router.callback_query(F.data == "profile:delete_confirm")
async def cb_delete_confirm(callback: CallbackQuery, lang: str = "uz"):
    kb = get_delete_confirm_keyboard(lang)
    if callback.message:
        await callback.message.edit_text(t(lang, "profile.delete_confirm"), reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "profile:delete_execute")
async def cb_delete_execute(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    user_service = UserService(session)
    await user_service.delete_personal_data(callback.from_user.id)
    if callback.message:
        await callback.message.edit_text(t(lang, "profile.deleted_success"))
    await callback.answer()
