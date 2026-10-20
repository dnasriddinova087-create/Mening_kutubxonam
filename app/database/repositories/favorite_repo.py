
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Book, Favorite


class FavoriteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, user_id: int, book_id: int) -> bool:
        stmt = select(Favorite).where(Favorite.user_id == user_id, Favorite.book_id == book_id)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            return False
        fav = Favorite(user_id=user_id, book_id=book_id)
        self.session.add(fav)
        await self.session.commit()
        return True

    add_favorite = add

    async def remove(self, user_id: int, book_id: int) -> bool:
        stmt = delete(Favorite).where(Favorite.user_id == user_id, Favorite.book_id == book_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    remove_favorite = remove

    async def is_favorite(self, user_id: int, book_id: int) -> bool:
        stmt = select(func.count(Favorite.id)).where(
            Favorite.user_id == user_id, Favorite.book_id == book_id
        )
        count = (await self.session.execute(stmt)).scalar() or 0
        return count > 0

    async def get_user_favorites(
        self, user_id: int, offset: int = 0, limit: int = 20
    ) -> list[Book]:
        stmt = (
            select(Book)
            .join(Favorite, Favorite.book_id == Book.id)
            .where(Favorite.user_id == user_id, Book.is_archived.is_(False))
            .order_by(Favorite.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = (await self.session.execute(stmt)).scalars().all()
        return list(items)

    async def count_user_favorites(self, user_id: int) -> int:
        stmt = select(func.count(Favorite.id)).where(Favorite.user_id == user_id)
        return (await self.session.execute(stmt)).scalar() or 0
