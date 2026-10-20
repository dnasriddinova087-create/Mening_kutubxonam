from abc import ABC, abstractmethod

from app.schemas.analysis import BookAnalysisDTO
from app.schemas.book import BookDTO


class BaseBookProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the provider (e.g. google_books, open_library, local)."""
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[BookDTO]:
        """Search books by title, author, or ISBN."""
        pass

    @abstractmethod
    async def get_by_id(self, source_book_id: str) -> BookDTO | None:
        """Retrieve detailed book information by its provider ID."""
        pass


class BaseAnalysisProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def analyze_book(self, book: BookDTO, language: str = "uz") -> BookAnalysisDTO:
        """Analyze book themes, summary, lessons, target audience."""
        pass

    @abstractmethod
    async def ask_question(self, book: BookDTO, question: str, language: str = "uz") -> str:
        """Answer a user question based on book metadata."""
        pass
