from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import BookAnalysis


class AnalysisRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_book_and_lang(
        self, book_id: int, language: str, analysis_type: str = "summary"
    ) -> BookAnalysis | None:
        stmt = (
            select(BookAnalysis)
            .where(
                BookAnalysis.book_id == book_id,
                BookAnalysis.language == language,
                BookAnalysis.analysis_type == analysis_type,
            )
            .order_by(BookAnalysis.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def save_analysis(
        self,
        book_id: int,
        language: str,
        content: dict[str, Any],
        provider: str,
        model: str,
        analysis_type: str = "summary",
    ) -> BookAnalysis:
        analysis = BookAnalysis(
            book_id=book_id,
            language=language,
            content=content,
            provider=provider,
            model=model,
            analysis_type=analysis_type,
        )
        self.session.add(analysis)
        await self.session.commit()
        await self.session.refresh(analysis)
        return analysis
