
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.book_repo import book_to_dto
from app.database.repositories.reading_list_repo import ReadingListRepository
from app.schemas.book import BookDTO


class ReadingListService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ReadingListRepository(session)

    async def update_status(self, user_id: int, book_id: int, status: str) -> None:
        await self.repo.set_status(user_id, book_id, status)

    async def remove_item(self, user_id: int, book_id: int) -> bool:
        return await self.repo.remove(user_id, book_id)

    async def get_items(
        self, user_id: int, status: str | None = None, offset: int = 0, limit: int = 20
    ) -> list[tuple[str, BookDTO]]:
        rows = await self.repo.get_user_items(user_id, status=status, offset=offset, limit=limit)
        return [(item.status, book_to_dto(book)) for item, book in rows]

    async def get_status_counts(self, user_id: int) -> dict[str, int]:
        return await self.repo.count_by_status(user_id)
