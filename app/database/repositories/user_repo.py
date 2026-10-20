from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Favorite, ReadingList, SearchHistory, User, UserNote


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None = None,
        full_name: str | None = None,
        language: str = "uz",
    ) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            # Update info if changed
            changed = False
            if username and user.username != username:
                user.username = username
                changed = True
            if full_name and user.full_name != full_name:
                user.full_name = full_name
                changed = True
            user.last_active_at = datetime.now(UTC)
            if changed:
                await self.session.commit()
            return user, False

        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            language=language,
            preferred_book_languages=[language],
            last_active_at=datetime.now(UTC),
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user, True

    async def update_language(self, telegram_id: int, language: str) -> bool:
        stmt = (
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(
                language=language,
                preferred_book_languages=[language],
                updated_at=datetime.now(UTC),
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def update_preferred_book_languages(
        self, telegram_id: int, languages: list[str]
    ) -> bool:
        stmt = (
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(
                preferred_book_languages=languages,
                updated_at=datetime.now(UTC),
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def update_reading_goal(self, telegram_id: int, goal: int) -> bool:
        stmt = (
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(reading_goal=max(1, goal), updated_at=datetime.now(UTC))
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def set_blocked(self, telegram_id: int, is_blocked: bool) -> bool:
        stmt = (
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(is_blocked=is_blocked, updated_at=datetime.now(UTC))
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_users_list(
        self, offset: int = 0, limit: int = 50, search: str | None = None
    ) -> tuple[list[User], int]:
        stmt = select(User)
        count_stmt = select(func.count(User.id))

        if search:
            filter_pattern = f"%{search}%"
            criteria = (User.username.ilike(filter_pattern)) | (User.full_name.ilike(filter_pattern))
            stmt = stmt.where(criteria)
            count_stmt = count_stmt.where(criteria)

        total = (await self.session.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(User.last_active_at.desc()).offset(offset).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()
        return list(items), total

    async def delete_user_personal_data(self, telegram_id: int) -> bool:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return False

        # Cascade deletes related favorites, reading_items, search_queries, notes
        await self.session.execute(delete(Favorite).where(Favorite.user_id == user.id))
        await self.session.execute(delete(ReadingList).where(ReadingList.user_id == user.id))
        await self.session.execute(delete(SearchHistory).where(SearchHistory.user_id == user.id))
        await self.session.execute(delete(UserNote).where(UserNote.user_id == user.id))
        await self.session.commit()
        return True
