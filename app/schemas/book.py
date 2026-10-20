from typing import Any

from pydantic import BaseModel, Field


class BookDTO(BaseModel):
    id: int | None = None
    source: str = Field(default="google_books", description="google_books, open_library, local")
    source_book_id: str = Field(description="Unique identifier from the provider")
    title: str
    original_title: str | None = None
    authors: list[str] = Field(default_factory=list)
    description: str | None = None
    summary: str | None = None
    main_idea: str | None = None
    key_lessons: str | None = None
    target_audience: str | None = None
    language: str | None = None
    genres: list[str] = Field(default_factory=list)
    publisher: str | None = None
    published_date: str | None = None
    isbn: str | None = None
    cover_url: str | None = None
    source_url: str | None = None
    reading_url: str | None = None
    access_type: str = Field(
        default="info",
        description="free (public domain), preview, borrow (open library), buy, info",
    )
    metadata_json: dict[str, Any] | None = None

    @property
    def authors_display(self) -> str:
        if self.authors:
            return ", ".join(self.authors)
        return "Noma'lum muallif"

    @property
    def genres_display(self) -> str:
        if self.genres:
            return ", ".join(self.genres[:3])
        return ""

    def deduplication_key(self) -> str:
        """Normalized key for detecting identical editions/books across sources."""
        if self.isbn:
            cleaned_isbn = "".join(filter(str.isalnum, self.isbn)).upper()
            if cleaned_isbn:
                return f"isbn:{cleaned_isbn}"
        clean_title = "".join(filter(str.isalnum, self.title.lower()))
        clean_author = "".join(filter(str.isalnum, (self.authors[0] if self.authors else "").lower()))
        return f"title_author:{clean_title}:{clean_author}"
