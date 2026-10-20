from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards.reply import get_main_menu_keyboard
from app.core.i18n import t

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext, lang: str = "uz"):
    await state.clear()
    user_name = message.from_user.first_name if message.from_user else "Kitobxon"
    welcome_text = t(lang, "welcome", name=user_name)
    reply_kb = get_main_menu_keyboard(lang)
    await message.answer(welcome_text, reply_markup=reply_kb, parse_mode="HTML")


@router.message(Command("help"))
@router.message(F.text.in_(["ℹ️ Yordam", "ℹ️ Помощь", "ℹ️ Help"]))
async def handle_help(message: Message, lang: str = "uz"):
    help_text = t(lang, "help_text")
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("cancel"))
async def handle_cancel(message: Message, state: FSMContext, lang: str = "uz"):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
    cancel_text = t(lang, "search.cancelled")
    reply_kb = get_main_menu_keyboard(lang)
    await message.answer(cancel_text, reply_markup=reply_kb)
