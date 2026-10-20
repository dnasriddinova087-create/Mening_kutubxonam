from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TgUser

from app.core.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES
from app.database.repositories.user_repo import UserRepository


class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        session = data.get("session")

        lang = DEFAULT_LOCALE

        if tg_user and session:
            user_repo = UserRepository(session)
            db_user = await user_repo.get_by_telegram_id(tg_user.id)

            if db_user:
                lang = db_user.language
                # If user is blocked, stop processing
                if db_user.is_blocked:
                    return None
            else:
                # Initial detection from Telegram app
                detected_lang = DEFAULT_LOCALE
                if tg_user.language_code:
                    code = tg_user.language_code.lower()[:2]
                    if code in SUPPORTED_LOCALES:
                        detected_lang = code

                db_user, _ = await user_repo.get_or_create(
                    telegram_id=tg_user.id,
                    username=tg_user.username,
                    full_name=tg_user.full_name,
                    language=detected_lang,
                )
                lang = db_user.language

        data["lang"] = lang
        return await handler(event, data)
