import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.favorite_repo import FavoriteRepository
from app.database.repositories.reading_list_repo import ReadingListRepository
from app.database.repositories.search_history_repo import SearchHistoryRepository
from app.database.repositories.user_repo import UserRepository


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.fav_repo = FavoriteRepository(session)
        self.reading_repo = ReadingListRepository(session)
        self.search_repo = SearchHistoryRepository(session)

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None = None,
        full_name: str | None = None,
        language: str = "uz",
    ):
        return await self.user_repo.get_or_create(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            language=language,
        )

    async def get_profile_summary(self, telegram_id: int) -> dict[str, Any] | None:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return None

        fav_count = await self.fav_repo.count_user_favorites(user.id)
        reading_counts = await self.reading_repo.count_by_status(user.id)
        search_count = await self.search_repo.count_user_searches(user.id)

        return {
            "user": user,
            "favorites_count": fav_count,
            "want_to_read": reading_counts.get("want_to_read", 0),
            "reading": reading_counts.get("reading", 0),
            "finished": reading_counts.get("finished", 0),
            "searches_count": search_count,
            "reading_goal": user.reading_goal,
        }

    async def log_search(self, telegram_id: int, query: str, result_count: int = 0) -> None:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if user:
            await self.search_repo.log_search(user.id, query, result_count)

    async def get_recent_searches(self, telegram_id: int, limit: int = 5) -> list[str]:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return []
        items = await self.search_repo.get_recent(user.id, limit=limit)
        return [it.query for it in items]

    async def export_data(self, telegram_id: int) -> str:
        """Export all user data as formatted JSON for GDPR compliance."""
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return "{}"

        favs = await self.fav_repo.get_user_favorites(user.id, limit=100)
        reading_items = await self.reading_repo.get_user_items(user.id, limit=100)
        searches = await self.search_repo.get_recent(user.id, limit=100)

        data = {
            "platform": "KITOBXON AI",
            "user": {
                "telegram_id": user.telegram_id,
                "username": user.username,
                "full_name": user.full_name,
                "language": user.language,
                "reading_goal": user.reading_goal,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            "favorites": [{"title": b.original_title, "authors": b.authors} for b in favs],
            "reading_list": [
                {"title": b.original_title, "status": item.status} for item, b in reading_items
            ],
            "search_history": [s.query for s in searches],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    async def delete_personal_data(self, telegram_id: int) -> bool:
        return await self.user_repo.delete_user_personal_data(telegram_id)
