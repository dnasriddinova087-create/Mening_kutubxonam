from aiogram import Router
from aiogram.types import ErrorEvent

from app.core.i18n import t
from app.core.logging import logger

router = Router(name="errors")


@router.error()
async def error_handler(event: ErrorEvent, lang: str = "uz"):
    logger.error(f"Telegram Bot Update Error: {event.exception}", exc_info=event.exception)

    user_msg = t(lang, "errors.general")

    if event.update.message:
        try:
            await event.update.message.answer(user_msg)
        except Exception:
            pass
    elif event.update.callback_query:
        try:
            await event.update.callback_query.answer(user_msg, show_alert=True)
        except Exception:
            pass
