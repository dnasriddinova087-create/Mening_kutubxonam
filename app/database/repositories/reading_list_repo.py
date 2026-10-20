from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Book, ReadingList


class ReadingListRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def set_status(self, user_id: int, book_id: int, status: str) -> ReadingList:
        stmt = select(ReadingList).where(
            ReadingList.user_id == user_id, ReadingList.book_id == book_id
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        now = datetime.now(UTC)

        if existing:
            existing.status = status
            if status == "finished":
                existing.finished_at = now
            await self.session.commit()
            return existing

        item = ReadingList(
            user_id=user_id,
            book_id=book_id,
            status=status,
            added_at=now,
            finished_at=now if status == "finished" else None,
        )
        self.session.add(item)
        await self.session.commit()
        return item

    async def remove(self, user_id: int, book_id: int) -> bool:
        stmt = delete(ReadingList).where(
            ReadingList.user_id == user_id, ReadingList.book_id == book_id
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_user_items(
        self, user_id: int, status: str | None = None, offset: int = 0, limit: int = 20
    ) -> list[tuple[ReadingList, Book]]:
        stmt = (
            select(ReadingList, Book)
            .join(Book, ReadingList.book_id == Book.id)
            .where(ReadingList.user_id == user_id, Book.is_archived.is_(False))
        )
        if status:
            stmt = stmt.where(ReadingList.status == status)
        stmt = stmt.order_by(ReadingList.added_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.all())

    async def count_by_status(self, user_id: int) -> dict[str, int]:
        stmt = (
            select(ReadingList.status, func.count(ReadingList.id))
            .where(ReadingList.user_id == user_id)
            .group_by(ReadingList.status)
        )
        rows = (await self.session.execute(stmt)).all()
        counts = {"want_to_read": 0, "reading": 0, "finished": 0}
        for status, count in rows:
            counts[status] = count
        return counts
