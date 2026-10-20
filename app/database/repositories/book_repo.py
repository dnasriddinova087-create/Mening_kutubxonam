from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Book
from app.schemas.book import BookDTO
from app.utils.translit import normalize_query


def book_to_dto(book: Book) -> BookDTO:
    return BookDTO(
        id=book.id,
        source=book.source,
        source_book_id=book.source_book_id,
        title=book.original_title,
        original_title=book.original_title,
        authors=book.authors or [],
        description=book.description,
        summary=book.metadata_json.get("summary") if book.metadata_json else None,
        main_idea=book.metadata_json.get("main_idea") if book.metadata_json else None,
        key_lessons=book.metadata_json.get("key_lessons") if book.metadata_json else None,
        target_audience=book.metadata_json.get("target_audience") if book.metadata_json else None,
        language=book.language,
        genres=book.genres or [],
        publisher=book.publisher,
        published_date=book.published_date,
        isbn=book.isbn,
        cover_url=book.cover_url,
        source_url=book.source_url,
        reading_url=book.reading_url,
        access_type=book.access_type or "info",
        metadata_json=book.metadata_json,
    )


class BookRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, book_id: int) -> Book | None:
        stmt = select(Book).where(Book.id == book_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_source(self, source: str, source_book_id: str) -> Book | None:
        stmt = select(Book).where(Book.source == source, Book.source_book_id == source_book_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_isbn(self, isbn: str) -> Book | None:
        clean_isbn = "".join(filter(str.isalnum, isbn))
        stmt = select(Book).where(Book.isbn.ilike(f"%{clean_isbn}%"))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def upsert_from_dto(self, dto: BookDTO) -> Book:
        existing = await self.get_by_source(dto.source, dto.source_book_id)
        if existing:
            # Update fields if richer data is available
            if not existing.cover_url and dto.cover_url:
                existing.cover_url = dto.cover_url
            if not existing.description and dto.description:
                existing.description = dto.description
            if not existing.isbn and dto.isbn:
                existing.isbn = dto.isbn
            if dto.reading_url and not existing.reading_url:
                existing.reading_url = dto.reading_url
            await self.session.commit()
            return existing

        normalized_title = normalize_query(dto.title).lower()
        new_book = Book(
            normalized_title=normalized_title,
            original_title=dto.title,
            authors=dto.authors,
            description=dto.description,
            language=dto.language,
            genres=dto.genres,
            publisher=dto.publisher,
            published_date=dto.published_date,
            isbn=dto.isbn,
            cover_url=dto.cover_url,
            source=dto.source,
            source_book_id=dto.source_book_id,
            source_url=dto.source_url,
            reading_url=dto.reading_url,
            access_type=dto.access_type,
            metadata_json=dto.metadata_json or {},
        )
        self.session.add(new_book)
        await self.session.commit()
        await self.session.refresh(new_book)
        return new_book

    async def search_local(
        self, query: str, offset: int = 0, limit: int = 20, include_archived: bool = False
    ) -> tuple[list[Book], int]:
        pattern = f"%{query}%"
        stmt = select(Book)
        count_stmt = select(func.count(Book.id))

        filters = [
            or_(
                Book.original_title.ilike(pattern),
                Book.normalized_title.ilike(pattern),
                Book.isbn.ilike(pattern),
                Book.publisher.ilike(pattern),
            )
        ]
        if not include_archived:
            filters.append(Book.is_archived.is_(False))

        stmt = stmt.where(*filters).offset(offset).limit(limit)
        count_stmt = count_stmt.where(*filters)

        total = (await self.session.execute(count_stmt)).scalar() or 0
        items = (await self.session.execute(stmt)).scalars().all()
        return list(items), total

    async def list_books(
        self,
        offset: int = 0,
        limit: int = 50,
        include_archived: bool = False,
        language: str | None = None,
        genre: str | None = None,
    ) -> tuple[list[Book], int]:
        from sqlalchemy import String, cast

        stmt = select(Book)
        count_stmt = select(func.count(Book.id))
        filters = []
        if not include_archived:
            filters.append(Book.is_archived.is_(False))
        if language and language.lower() not in ("all", "*"):
            filters.append(func.lower(Book.language) == language.lower())
        if genre and genre.lower() not in ("all", "*"):
            filters.append(cast(Book.genres, String).ilike(f"%{genre}%"))

        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)

        total = (await self.session.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(Book.id.desc()).offset(offset).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()
        return list(items), total

    async def set_archived(self, book_id: int, is_archived: bool) -> bool:
        stmt = (
            update(Book)
            .where(Book.id == book_id)
            .values(is_archived=is_archived, updated_at=datetime.now(UTC))
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def update_book_details(
        self,
        book_id: int,
        title: str,
        authors: list[str],
        description: str | None,
        cover_url: str | None,
        publisher: str | None,
        published_date: str | None,
        isbn: str | None,
        access_type: str,
        reading_url: str | None,
        language: str | None = None,
        genres: list[str] | None = None,
    ) -> bool:
        values: dict[str, Any] = {
            "original_title": title,
            "normalized_title": normalize_query(title).lower(),
            "authors": authors,
            "description": description,
            "cover_url": cover_url,
            "publisher": publisher,
            "published_date": published_date,
            "isbn": isbn,
            "access_type": access_type,
            "reading_url": reading_url,
            "updated_at": datetime.now(UTC),
        }
        if language is not None:
            values["language"] = language
        if genres is not None:
            values["genres"] = genres

        stmt = update(Book).where(Book.id == book_id).values(**values)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def delete_book(self, book_id: int) -> bool:
        from sqlalchemy import delete
        stmt = delete(Book).where(Book.id == book_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
