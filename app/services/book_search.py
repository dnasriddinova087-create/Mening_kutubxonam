import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.database.repositories.book_repo import BookRepository, book_to_dto
from app.providers.google_books import GoogleBooksProvider
from app.providers.local_catalog import LocalCatalogProvider
from app.providers.open_library import OpenLibraryProvider
from app.schemas.book import BookDTO
from app.utils.translit import cyrillic_to_latin, latin_to_cyrillic, normalize_query


class BookSearchService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.book_repo = BookRepository(session)
        self.local_provider = LocalCatalogProvider(session)
        self.google_provider = GoogleBooksProvider()
        self.openlibrary_provider = OpenLibraryProvider()

    def _deduplicate(self, books: list[BookDTO]) -> list[BookDTO]:
        """Deduplicate books based on ISBN or clean title + author."""
        seen: dict[str, BookDTO] = {}
        ordered: list[BookDTO] = []

        for b in books:
            key = b.deduplication_key()
            if key in seen:
                # Merge richer data if existing one lacks cover or description
                existing = seen[key]
                if not existing.cover_url and b.cover_url:
                    existing.cover_url = b.cover_url
                if not existing.description and b.description:
                    existing.description = b.description
                if not existing.isbn and b.isbn:
                    existing.isbn = b.isbn
                if not existing.reading_url and b.reading_url:
                    existing.reading_url = b.reading_url
            else:
                seen[key] = b
                ordered.append(b)
        return ordered

    async def search(self, raw_query: str, limit: int = 15) -> list[BookDTO]:
        query = normalize_query(raw_query)
        if not query:
            return []

        # 1. First run local, Google Books, and Open Library concurrently
        tasks = [
            self.local_provider.search(query, limit=5),
            self.google_provider.search(query, limit=10),
            self.openlibrary_provider.search(query, limit=5),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        merged: list[BookDTO] = []
        for res in results:
            if isinstance(res, list):
                merged.extend(res)
            elif isinstance(res, Exception):
                logger.warning(f"Provider search exception: {res}")

        # 2. Transliteration retry if few or no results
        if len(merged) < 3:
            alt_query = latin_to_cyrillic(query)
            if alt_query == query:
                alt_query = cyrillic_to_latin(query)

            if alt_query != query:
                logger.info(f"Retrying search with transliterated query: '{alt_query}'")
                extra_tasks = [
                    self.google_provider.search(alt_query, limit=5),
                    self.openlibrary_provider.search(alt_query, limit=5),
                ]
                extra_results = await asyncio.gather(*extra_tasks, return_exceptions=True)
                for res in extra_results:
                    if isinstance(res, list):
                        merged.extend(res)

        deduped = self._deduplicate(merged)

        # 3. Synchronize / persist top results to DB so they have internal IDs for callbacks
        persisted_dtos: list[BookDTO] = []
        for dto in deduped[:limit]:
            try:
                db_book = await self.book_repo.upsert_from_dto(dto)
                persisted_dto = book_to_dto(db_book)
                persisted_dtos.append(persisted_dto)
            except Exception as e:
                logger.warning(f"Failed to cache book {dto.title} in DB: {e}")
                persisted_dtos.append(dto)

        return persisted_dtos

    async def get_book_by_id(self, book_id: int) -> BookDTO | None:
        book = await self.book_repo.get_by_id(book_id)
        if book:
            return book_to_dto(book)
        return None
