from aiogram.filters import BaseFilter
from aiogram.types import Message, User

from app.core.config import settings


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | User) -> bool:
        user_id = event.from_user.id if isinstance(event, Message) else event.id
        return user_id in settings.ADMIN_TELEGRAM_IDS
