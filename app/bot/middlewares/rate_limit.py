import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from app.core.i18n import t


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit_seconds: float = 0.6):
        self.limit_seconds = limit_seconds
        self.last_user_time: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        now = time.monotonic()
        last_time = self.last_user_time.get(user.id, 0.0)

        if now - last_time < self.limit_seconds:
            lang = data.get("lang", "uz")
            warning = t(lang, "errors.rate_limit")

            if isinstance(event, Message):
                await event.answer(warning)
            elif isinstance(event, CallbackQuery):
                await event.answer(warning, show_alert=True)
            return None

        self.last_user_time[user.id] = now
        return await handler(event, data)
