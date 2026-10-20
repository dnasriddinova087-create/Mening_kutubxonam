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
        code=book.code,
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
        file_url=book.file_url,
        file_format=book.file_format or "PDF",
        audio_url=book.audio_url,
        audio_duration=book.audio_duration,
        video_url=book.video_url,
        extra_materials=book.extra_materials or [],
        ai_analysis=book.ai_analysis or {},
        status=book.status or "published",
        pages=book.pages,
        translations=book.translations or {},
        metadata_json=book.metadata_json,
    )


class BookRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, book_id: int) -> Book | None:
        stmt = select(Book).where(Book.id == book_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: int) -> Book | None:
        """Fetch book by sequential unique integer code."""
        stmt = select(Book).where(Book.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_next_book_code(self) -> int:
        """Calculate next available sequential book code starting from 1."""
        stmt = select(func.coalesce(func.max(Book.code), 0))
        max_code = (await self.session.execute(stmt)).scalar() or 0
        return max_code + 1

    async def assign_missing_codes(self) -> int:
        """Assign sequential codes to any books that currently do not have a code."""
        stmt = select(Book).where(Book.code.is_(None)).order_by(Book.id.asc())
        books_without_code = (await self.session.execute(stmt)).scalars().all()
        if not books_without_code:
            return 0

        next_code = await self.get_next_book_code()
        count = 0
        for book in books_without_code:
            book.code = next_code
            next_code += 1
            count += 1
        await self.session.commit()
        return count

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
            if dto.file_url and not existing.file_url:
                existing.file_url = dto.file_url
            if dto.audio_url and not existing.audio_url:
                existing.audio_url = dto.audio_url
            if dto.video_url and not existing.video_url:
                existing.video_url = dto.video_url
            if dto.code and not existing.code:
                existing.code = dto.code
            elif not existing.code:
                existing.code = await self.get_next_book_code()
            await self.session.commit()
            return existing

        code = dto.code
        if code is None:
            code = await self.get_next_book_code()

        normalized_title = normalize_query(dto.title).lower()
        new_book = Book(
            code=code,
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
            file_url=dto.file_url,
            file_format=dto.file_format or "PDF",
            audio_url=dto.audio_url,
            audio_duration=dto.audio_duration,
            video_url=dto.video_url,
            extra_materials=dto.extra_materials or [],
            ai_analysis=dto.ai_analysis or {},
            status=dto.status or "published",
            pages=dto.pages,
            translations=dto.translations or {},
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
        code: int | None = None,
        file_url: str | None = None,
        file_format: str | None = None,
        audio_url: str | None = None,
        audio_duration: str | None = None,
        video_url: str | None = None,
        extra_materials: list[dict[str, Any]] | None = None,
        ai_analysis: dict[str, Any] | None = None,
        status: str | None = None,
        pages: int | None = None,
        translations: dict[str, Any] | None = None,
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
        if code is not None:
            values["code"] = code
        if file_url is not None:
            values["file_url"] = file_url
        if file_format is not None:
            values["file_format"] = file_format
        if audio_url is not None:
            values["audio_url"] = audio_url
        if audio_duration is not None:
            values["audio_duration"] = audio_duration
        if video_url is not None:
            values["video_url"] = video_url
        if extra_materials is not None:
            values["extra_materials"] = extra_materials
        if ai_analysis is not None:
            values["ai_analysis"] = ai_analysis
        if status is not None:
            values["status"] = status
        if pages is not None:
            values["pages"] = pages
        if translations is not None:
            values["translations"] = translations

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
