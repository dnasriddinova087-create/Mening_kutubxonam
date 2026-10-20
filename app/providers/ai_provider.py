import json
import re

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.providers.base import BaseAnalysisProvider
from app.schemas.analysis import BookAnalysisDTO
from app.schemas.book import BookDTO


class MetadataAnalysisProvider(BaseAnalysisProvider):
    """Fallback provider when no AI API key is configured or external AI is offline."""

    @property
    def provider_name(self) -> str:
        return "metadata_heuristic"

    async def analyze_book(self, book: BookDTO, language: str = "uz") -> BookAnalysisDTO:
        authors = book.authors_display
        genres = ", ".join(book.genres) if book.genres else ("adabiyot" if language == "uz" else "literature")
        desc = book.description or ""

        if language == "ru":
            summary = (
                f"Книга '{book.title}' автора {authors} относится к категории {genres}. "
                + (desc[:300] + "..." if len(desc) > 300 else desc or "Классическое произведение.")
            )
            key_ideas = [
                f"Исследование вопросов и тем жанра {genres}.",
                f"Художественный или познавательный вклад автора {authors}.",
                "Развитие ключевых персонажей и концепций произведения.",
            ]
            lessons = [
                "Глубокое понимание контекста и замысла автора.",
                "Критическое осмысление представленных идей.",
            ]
            audience = f"Любители жанра {genres}, исследователи и вдумчивые читатели."
            similar = [f"Другие известные книги автора {authors}"]
        elif language == "en":
            summary = (
                f"'{book.title}' by {authors} falls within the genre of {genres}. "
                + (desc[:300] + "..." if len(desc) > 300 else desc or "A noteworthy work.")
            )
            key_ideas = [
                f"Exploration of foundational themes in {genres}.",
                f"Narrative and intellectual contribution of {authors}.",
                "Core conflicts and thematic development.",
            ]
            lessons = [
                "Appreciation of the author's stylistic and philosophical insights.",
                "Practical reflection on the core narrative.",
            ]
            audience = f"Readers interested in {genres} and works by {authors}."
            similar = [f"Other prominent works by {authors}"]
        else:  # uz
            summary = (
                f"'{book.title}' asari muallif {authors} tomonidan yaratilgan bo'lib, {genres} yo'nalishiga mansub. "
                + (desc[:300] + "..." if len(desc) > 300 else desc or "Ushbu asar o'z yo'nalishida muhim ahamiyatga ega.")
            )
            key_ideas = [
                f"{genres} sohasidagi dolzarb g'oya va mavzular tahlili.",
                f"{authors} tomonidan ilgari surilgan falsafiy yoki amaliy qarashlar.",
                "Insoniy munosabatlar va axloqiy qadriyatlar rivoji.",
            ]
            lessons = [
                "Asardan o'z hayotimiz va fikrlashimiz uchun to'g'ri xulosa chiqarish.",
                "Muallif ko'targan masalalarga chuqur nazar tashlash.",
            ]
            audience = f"{genres} ixlosmandlari, talabalar va keng kitobxonlar ommasi."
            similar = [f"{authors}ning boshqa durdona asarlari"]

        return BookAnalysisDTO(
            summary=summary,
            key_ideas=key_ideas,
            lessons=lessons,
            target_audience=audience,
            similar_books=similar,
            provider="metadata_fallback",
            model="heuristic-v1",
        )

    async def ask_question(self, book: BookDTO, question: str, language: str = "uz") -> str:
        if language == "ru":
            return (
                f"На основе метаданных книги '{book.title}' (автор: {book.authors_display}): "
                "ИИ-модель работает в базовом режиме метаданных. "
                f"Книга относится к жанру {', '.join(book.genres) or 'Общая литература'}."
            )
        elif language == "en":
            return (
                f"Based on metadata for '{book.title}' by {book.authors_display}: "
                "AI analysis is in basic metadata mode. "
                f"Genres: {', '.join(book.genres) or 'General'}."
            )
        else:
            return (
                f"'{book.title}' ({book.authors_display}) kitobi metama'lumotlari asosida: "
                "AI xizmati hozirda metama'lumotlar rejimida ishlamoqda. "
                f"Janri: {', '.join(book.genres) or 'Umumiy adabiyot'}."
            )


class GeminiAnalysisProvider(BaseAnalysisProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.AI_API_KEY
        self.model = model or settings.AI_MODEL or "gemini-1.5-flash"
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.fallback = MetadataAnalysisProvider()

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def analyze_book(self, book: BookDTO, language: str = "uz") -> BookAnalysisDTO:
        if not self.api_key:
            logger.info("No Gemini API key provided, using fallback metadata analysis.")
            return await self.fallback.analyze_book(book, language)

        prompt = f"""
You are an expert literary critic and book discovery engine for Kitobxon AI.
Analyze the following book using its metadata and your literary knowledge.
Output ONLY valid JSON (no markdown formatting, no code blocks) matching this schema:
{{
  "summary": "Concise 2-3 sentence synopsis in {language}",
  "key_ideas": ["Main theme 1 in {language}", "Main theme 2 in {language}", "Main theme 3 in {language}"],
  "lessons": ["Key actionable/philosophical takeaway 1 in {language}", "Takeaway 2 in {language}"],
  "target_audience": "Who this book is ideal for in {language}",
  "similar_books": ["Title 1 by Author", "Title 2 by Author"]
}}

Book Information:
Title: {book.title}
Authors: {book.authors_display}
Published: {book.published_date}
Genres: {", ".join(book.genres)}
Publisher: {book.publisher}
Description: {book.description or "N/A"}
Language for response: {language}
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 800},
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.base_url}?key={self.api_key}",
                    json=payload,
                )
                if resp.status_code != 200:
                    logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text}")
                    return await self.fallback.analyze_book(book, language)

                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Clean up any potential markdown backticks
                raw_text = re.sub(r"^```json\s*", "", raw_text, flags=re.MULTILINE)
                raw_text = re.sub(r"^```\s*", "", raw_text, flags=re.MULTILINE)
                raw_text = re.sub(r"```$", "", raw_text, flags=re.MULTILINE).strip()

                parsed = json.loads(raw_text)
                return BookAnalysisDTO(
                    summary=parsed.get("summary", ""),
                    key_ideas=parsed.get("key_ideas", []),
                    lessons=parsed.get("lessons", []),
                    target_audience=parsed.get("target_audience", ""),
                    similar_books=parsed.get("similar_books", []),
                    provider="gemini",
                    model=self.model,
                )
        except Exception as e:
            logger.warning(f"Gemini API analysis failed: {e}. Reverting to fallback.")
            return await self.fallback.analyze_book(book, language)

    async def ask_question(self, book: BookDTO, question: str, language: str = "uz") -> str:
        if not self.api_key:
            return await self.fallback.ask_question(book, question, language)

        prompt = f"""
Book: {book.title} by {book.authors_display}
Description: {book.description or "N/A"}
User Question: {question}
Language: {language}

Answer concisely, politely, and strictly based on verifiable metadata and knowledge in {language}.
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.5, "maxOutputTokens": 500},
        }
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(
                    f"{self.base_url}?key={self.api_key}",
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logger.warning(f"Gemini ask_question failed: {e}")

        return await self.fallback.ask_question(book, question, language)


def get_ai_provider() -> BaseAnalysisProvider:
    """Factory creating appropriate AI provider based on settings."""
    if settings.AI_PROVIDER == "gemini" and settings.AI_API_KEY:
        return GeminiAnalysisProvider(api_key=settings.AI_API_KEY, model=settings.AI_MODEL)
    return MetadataAnalysisProvider()
