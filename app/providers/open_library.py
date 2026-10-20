from typing import Any

import httpx

from app.core.logging import logger
from app.providers.base import BaseBookProvider
from app.schemas.book import BookDTO


class OpenLibraryProvider(BaseBookProvider):
    def __init__(self):
        self.search_url = "https://openlibrary.org/search.json"
        self.base_url = "https://openlibrary.org"
        self.timeout = 10.0

    @property
    def name(self) -> str:
        return "open_library"

    def _parse_doc(self, doc: dict[str, Any]) -> BookDTO | None:
        try:
            key = doc.get("key")  # e.g. /works/OL45883W
            if not key:
                return None
            clean_id = key.strip("/").replace("works/", "")

            title = doc.get("title")
            if not title:
                return None

            authors = doc.get("author_name", [])
            published_date = str(doc.get("first_publish_year")) if doc.get("first_publish_year") else None
            publisher = doc.get("publisher", [None])[0] if doc.get("publisher") else None
            genres = doc.get("subject", [])[:5] if doc.get("subject") else []
            language = doc.get("language", [None])[0] if doc.get("language") else None

            # ISBN
            isbn = None
            if doc.get("isbn"):
                isbn = doc["isbn"][0]

            # Cover
            cover_i = doc.get("cover_i")
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg" if cover_i else None

            # Legal access
            source_url = f"{self.base_url}{key}"
            has_fulltext = doc.get("has_fulltext", False)
            public_scan = doc.get("public_scan_b", False)
            lending_edition = doc.get("lending_edition_s")

            access_type = "info"
            reading_url = source_url

            if public_scan:
                access_type = "free"
                reading_url = f"{source_url}/borrow"
            elif lending_edition:
                access_type = "borrow"
                reading_url = f"{source_url}/borrow"
            elif has_fulltext:
                access_type = "preview"

            return BookDTO(
                source=self.name,
                source_book_id=clean_id,
                title=title,
                authors=authors,
                description=None,  # Search API returns subjects/title; works endpoint needed for full text if requested
                language=language,
                genres=genres,
                publisher=publisher,
                published_date=published_date,
                isbn=isbn,
                cover_url=cover_url,
                source_url=source_url,
                reading_url=reading_url,
                access_type=access_type,
                metadata_json={"openlibrary_key": key},
            )
        except Exception as e:
            logger.warning(f"Error parsing Open Library doc: {e}")
            return None

    async def search(self, query: str, limit: int = 10) -> list[BookDTO]:
        params = {
            "q": query,
            "limit": min(limit, 20),
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.search_url, params=params)
                if resp.status_code != 200:
                    logger.warning(f"Open Library search returned status {resp.status_code}")
                    return []
                data = resp.json()
                docs = data.get("docs", [])
                results = []
                for doc in docs:
                    book = self._parse_doc(doc)
                    if book:
                        results.append(book)
                return results
        except Exception as e:
            logger.warning(f"Open Library search failed: {e}")
            return []

    async def get_by_id(self, source_book_id: str) -> BookDTO | None:
        url = f"{self.base_url}/works/{source_book_id}.json"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                title = data.get("title", "")
                desc = data.get("description")
                if isinstance(desc, dict):
                    desc = desc.get("value", "")

                return BookDTO(
                    source=self.name,
                    source_book_id=source_book_id,
                    title=title,
                    description=desc,
                    source_url=f"{self.base_url}/works/{source_book_id}",
                    access_type="info",
                )
        except Exception as e:
            logger.warning(f"Open Library get_by_id failed: {e}")
            return None
