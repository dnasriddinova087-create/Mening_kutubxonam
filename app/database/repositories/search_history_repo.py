
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import SearchHistory


class SearchHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_search(self, user_id: int, query: str, result_count: int = 0) -> SearchHistory:
        item = SearchHistory(
            user_id=user_id,
            query=query[:255],
            result_count=result_count,
        )
        self.session.add(item)
        await self.session.commit()
        return item

    async def get_recent(self, user_id: int, limit: int = 5) -> list[SearchHistory]:
        stmt = (
            select(SearchHistory)
            .where(SearchHistory.user_id == user_id)
            .order_by(SearchHistory.created_at.desc())
            .limit(limit)
        )
        items = (await self.session.execute(stmt)).scalars().all()
        return list(items)

    async def count_user_searches(self, user_id: int) -> int:
        stmt = select(func.count(SearchHistory.id)).where(SearchHistory.user_id == user_id)
        return (await self.session.execute(stmt)).scalar() or 0

    async def get_top_queries(self, limit: int = 10) -> list[tuple[str, int]]:
        stmt = (
            select(SearchHistory.query, func.count(SearchHistory.id).label("cnt"))
            .group_by(SearchHistory.query)
            .order_by(desc("cnt"))
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(r[0], r[1]) for r in rows]

    async def count_total_searches(self) -> int:
        stmt = select(func.count(SearchHistory.id))
        return (await self.session.execute(stmt)).scalar() or 0
