from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import t
from app.services.recommendations import RecommendationService

router = Router(name="recommendations")


@router.message(Command("recommend"))
@router.message(F.text.in_(["✨ Kitob tavsiya qilish", "✨ Рекомендации", "✨ Recommendations"]))
async def handle_recommendations(message: Message, session: AsyncSession, lang: str = "uz"):
    service = RecommendationService(session)
    recs = await service.get_recommendations(language=lang, limit=5)

    if not recs:
        await message.answer(t(lang, "recommendations.empty"))
        return

    buttons = []
    for b in recs:
        if b.id:
            label = f"✨ {b.title} — {b.authors_display}"
            buttons.append([InlineKeyboardButton(text=label[:45], callback_data=f"book:view:{b.id}")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = f"{t(lang, 'recommendations.title')}\n{t(lang, 'recommendations.subtitle')}"
    await message.answer(text, reply_markup=kb, parse_mode="HTML")
