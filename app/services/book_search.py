import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.database.repositories.book_repo import BookRepository, book_to_dto
from app.providers.google_books import GoogleBooksProvider
from app.providers.local_catalog import LocalCatalogProvider
from app.providers.open_library import OpenLibraryProvider
from app.schemas.book import BookDTO
from app.utils.translit import cyrillic_to_latin, latin_to_cyrillic, normalize_query


def _normalize_lang_code(code: str | None) -> str:
    if not code:
        return ""
    c = code.strip().lower()
    if c in ("uz", "uzb", "uzbek"):
        return "uz"
    if c in ("ru", "rus", "russian"):
        return "ru"
    if c in ("en", "eng", "english"):
        return "en"
    return c[:2]


def _score_book(b: BookDTO, query_lower: str, pref_langs: set[str], iface_lang: str) -> float:
    score = 0.0
    book_lang = _normalize_lang_code(b.language)

    # 1. Language priority
    if book_lang and book_lang in pref_langs:
        score += 150.0
    elif book_lang and book_lang == iface_lang:
        score += 100.0
    elif not book_lang:
        score += 20.0  # unknown language, don't penalize completely
    else:
        score += 0.0  # different language

    # 2. Query relevance
    title_lower = (b.title or "").lower()
    if query_lower:
        if query_lower == title_lower:
            score += 60.0
        elif title_lower.startswith(query_lower):
            score += 35.0
        elif query_lower in title_lower:
            score += 25.0

    for author in (b.authors or []):
        if query_lower in author.lower():
            score += 30.0
            break

    if b.isbn and query_lower in b.isbn.lower().replace("-", ""):
        score += 200.0

    # 3. Source preference (local curated catalog highest)
    if b.source == "local":
        score += 50.0

    # 4. Metadata richness
    if b.cover_url:
        score += 15.0
    if b.description:
        score += 10.0
    if b.reading_url:
        score += 10.0

    return score


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
                if not existing.language and b.language:
                    existing.language = b.language
            else:
                seen[key] = b
                ordered.append(b)
        return ordered

    async def search(
        self,
        raw_query: str,
        limit: int = 15,
        preferred_languages: list[str] | None = None,
        interface_language: str = "uz",
    ) -> list[BookDTO]:
        query = normalize_query(raw_query)
        if not query:
            return []

        # Resolve preferred languages
        resolved_pref_langs: list[str] = (
            [lang_code.lower() for lang_code in preferred_languages]
            if preferred_languages
            else [interface_language.lower()]
        )
        pref_langs_set = set(resolved_pref_langs)
        primary_lang = resolved_pref_langs[0] if len(resolved_pref_langs) == 1 else None

        # 1. Run local catalog, Google Books, and Open Library concurrently
        tasks = [
            self.local_provider.search(query, limit=5),
            self.google_provider.search(query, limit=10, lang_restrict=primary_lang),
            self.openlibrary_provider.search(query, limit=5, lang_code=primary_lang),
        ]

        # If primary lang specified, also fetch broad google books in background to avoid missing
        if primary_lang:
            tasks.append(self.google_provider.search(query, limit=5))

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
                    self.google_provider.search(alt_query, limit=5, lang_restrict=primary_lang),
                    self.openlibrary_provider.search(alt_query, limit=5, lang_code=primary_lang),
                ]
                extra_results = await asyncio.gather(*extra_tasks, return_exceptions=True)
                for res in extra_results:
                    if isinstance(res, list):
                        merged.extend(res)

        deduped = self._deduplicate(merged)

        # 3. Sort by language priority and relevance score
        q_lower = query.lower()
        scored_books = [
            (_score_book(b, q_lower, pref_langs_set, interface_language.lower()), b)
            for b in deduped
        ]
        scored_books.sort(key=lambda item: item[0], reverse=True)
        ranked = [b for _, b in scored_books]

        # 4. Synchronize / persist top results to DB so they have internal IDs for callbacks
        persisted_dtos: list[BookDTO] = []
        for dto in ranked[:limit]:
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
