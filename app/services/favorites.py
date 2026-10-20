
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.book_repo import book_to_dto
from app.database.repositories.favorite_repo import FavoriteRepository
from app.schemas.book import BookDTO


class FavoritesService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = FavoriteRepository(session)

    async def toggle_favorite(self, user_id: int, book_id: int) -> bool:
        """Toggle favorite status. Returns True if added, False if removed."""
        is_fav = await self.repo.is_favorite(user_id, book_id)
        if is_fav:
            await self.repo.remove(user_id, book_id)
            return False
        else:
            await self.repo.add(user_id, book_id)
            return True

    async def is_favorite(self, user_id: int, book_id: int) -> bool:
        return await self.repo.is_favorite(user_id, book_id)

    async def get_favorites(self, user_id: int, offset: int = 0, limit: int = 20) -> list[BookDTO]:
        books = await self.repo.get_user_favorites(user_id, offset=offset, limit=limit)
        return [book_to_dto(b) for b in books]

    async def count_favorites(self, user_id: int) -> int:
        return await self.repo.count_user_favorites(user_id)
