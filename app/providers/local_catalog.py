
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.book_repo import BookRepository, book_to_dto
from app.providers.base import BaseBookProvider
from app.schemas.book import BookDTO


class LocalCatalogProvider(BaseBookProvider):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BookRepository(session)

    @property
    def name(self) -> str:
        return "local"

    async def search(self, query: str, limit: int = 10) -> list[BookDTO]:
        books, _ = await self.repo.search_local(query, offset=0, limit=limit, include_archived=False)
        return [book_to_dto(b) for b in books]

    async def get_by_id(self, source_book_id: str) -> BookDTO | None:
        try:
            book_id = int(source_book_id)
            book = await self.repo.get_by_id(book_id)
            if book and not book.is_archived:
                return book_to_dto(book)
            return None
        except ValueError:
            return None
