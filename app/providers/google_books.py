from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.providers.base import BaseBookProvider
from app.schemas.book import BookDTO


class GoogleBooksProvider(BaseBookProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.GOOGLE_BOOKS_API_KEY
        self.base_url = "https://www.googleapis.com/books/v1/volumes"
        self.timeout = 10.0

    @property
    def name(self) -> str:
        return "google_books"

    def _parse_volume(self, item: dict[str, Any]) -> BookDTO | None:
        try:
            vol_id = item.get("id")
            if not vol_id:
                return None
            info = item.get("volumeInfo", {})
            access = item.get("accessInfo", {})
            sale = item.get("saleInfo", {})

            title = info.get("title")
            if not title:
                return None

            authors = info.get("authors", [])
            published_date = info.get("publishedDate")
            publisher = info.get("publisher")
            description = info.get("description")
            genres = info.get("categories", [])
            language = info.get("language")

            # ISBN
            isbn = None
            for id_dict in info.get("industryIdentifiers", []):
                t = id_dict.get("type")
                if t in ("ISBN_13", "ISBN_10"):
                    isbn = id_dict.get("identifier")
                    if t == "ISBN_13":
                        break

            # Cover image (upgrade http to https)
            image_links = info.get("imageLinks", {})
            cover_url = (
                image_links.get("extraLarge")
                or image_links.get("large")
                or image_links.get("medium")
                or image_links.get("thumbnail")
            )
            if cover_url and cover_url.startswith("http://"):
                cover_url = cover_url.replace("http://", "https://", 1)

            # Access and legal reading links
            access_view = access.get("accessViewStatus", "")
            is_public_domain = access.get("publicDomain", False)
            web_reader_link = access.get("webReaderLink")
            preview_link = info.get("previewLink")
            info_link = info.get("infoLink")
            buy_link = sale.get("buyLink")

            reading_url = None
            access_type = "info"

            if is_public_domain or access_view == "FULL_PUBLIC_DOMAIN":
                access_type = "free"
                reading_url = web_reader_link or preview_link
            elif access_view in ("SAMPLE", "PARTIAL"):
                access_type = "preview"
                reading_url = preview_link or web_reader_link
            elif sale.get("saleability") == "FOR_SALE" and buy_link:
                access_type = "buy"
                reading_url = buy_link
            else:
                reading_url = info_link

            return BookDTO(
                source=self.name,
                source_book_id=vol_id,
                title=title,
                authors=authors,
                description=description,
                language=language,
                genres=genres,
                publisher=publisher,
                published_date=published_date,
                isbn=isbn,
                cover_url=cover_url,
                source_url=info_link,
                reading_url=reading_url,
                access_type=access_type,
                metadata_json={"raw_google_id": vol_id, "access_view": access_view},
            )
        except Exception as e:
            logger.warning(f"Error parsing Google Books volume: {e}")
            return None

    async def search(self, query: str, limit: int = 10, lang_restrict: str | None = None, **kwargs) -> list[BookDTO]:
        import asyncio
        params: dict[str, Any] = {
            "q": query,
            "maxResults": min(limit, 40),
            "printType": "books",
        }
        if lang_restrict:
            # Google Books accepts 2-letter codes, e.g. 'uz', 'ru', 'en'
            clean_code = lang_restrict.lower()
            if clean_code in ("uzb", "uz"):
                params["langRestrict"] = "uz"
            elif clean_code in ("rus", "ru"):
                params["langRestrict"] = "ru"
            elif clean_code in ("eng", "en"):
                params["langRestrict"] = "en"
            else:
                params["langRestrict"] = clean_code[:2]

        if self.api_key:
            params["key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.base_url, params=params)
                if resp.status_code == 429:
                    logger.warning("Google Books API rate limited (429). Retrying after 1s...")
                    await asyncio.sleep(1.0)
                    resp = await client.get(self.base_url, params=params)

                if resp.status_code != 200:
                    logger.warning(f"Google Books API returned status {resp.status_code}")
                    return []
                data = resp.json()
                items = data.get("items", [])
                results = []
                for item in items:
                    book = self._parse_volume(item)
                    if book:
                        results.append(book)
                return results
        except Exception as e:
            logger.warning(f"Google Books API search failed: {e}")
            return []

    async def get_by_id(self, source_book_id: str) -> BookDTO | None:
        url = f"{self.base_url}/{source_book_id}"
        params = {}
        if self.api_key:
            params["key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return None
                return self._parse_volume(resp.json())
        except Exception as e:
            logger.warning(f"Google Books API get_by_id failed for {source_book_id}: {e}")
            return None
