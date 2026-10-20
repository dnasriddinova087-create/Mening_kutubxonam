from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.analysis_repo import AnalysisRepository
from app.providers.ai_provider import get_ai_provider
from app.schemas.analysis import BookAnalysisDTO
from app.schemas.book import BookDTO


class BookAnalysisService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AnalysisRepository(session)
        self.ai = get_ai_provider()

    async def get_or_create_analysis(
        self, book: BookDTO, language: str = "uz"
    ) -> BookAnalysisDTO:
        if book.id:
            cached = await self.repo.get_by_book_and_lang(book.id, language, analysis_type="summary")
            if cached and cached.content:
                data = cached.content
                return BookAnalysisDTO(
                    summary=data.get("summary", ""),
                    key_ideas=data.get("key_ideas", []),
                    lessons=data.get("lessons", []),
                    target_audience=data.get("target_audience", ""),
                    similar_books=data.get("similar_books", []),
                    provider=cached.provider,
                    model=cached.model,
                )

        # Generate fresh analysis
        analysis = await self.ai.analyze_book(book, language=language)

        # Save to DB cache if book has DB ID
        if book.id:
            await self.repo.save_analysis(
                book_id=book.id,
                language=language,
                content=analysis.model_dump(),
                provider=analysis.provider,
                model=analysis.model,
                analysis_type="summary",
            )

        return analysis

    async def ask_question(self, book: BookDTO, question: str, language: str = "uz") -> str:
        return await self.ai.ask_question(book, question, language=language)
