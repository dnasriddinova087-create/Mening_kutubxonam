import pytest

from app.providers.ai_provider import MetadataAnalysisProvider
from app.schemas.book import BookDTO


@pytest.mark.asyncio
async def test_metadata_analysis_fallback():
    provider = MetadataAnalysisProvider()
    book = BookDTO(
        source="local",
        source_book_id="loc_test",
        title="Boburnoma",
        authors=["Zahiriddin Muhammad Bobur"],
        description="Boburning buyuk memuar asari, tarixiy va adabiy yodgorlik.",
        genres=["Memuar", "Tarix"],
    )

    analysis_uz = await provider.analyze_book(book, language="uz")
    assert analysis_uz is not None
    assert len(analysis_uz.summary) > 0
    assert len(analysis_uz.key_ideas) > 0
    assert len(analysis_uz.lessons) > 0
    assert "Bobur" in analysis_uz.summary

    analysis_ru = await provider.analyze_book(book, language="ru")
    assert "автора" in analysis_ru.summary

    analysis_en = await provider.analyze_book(book, language="en")
    assert "falls within" in analysis_en.summary
