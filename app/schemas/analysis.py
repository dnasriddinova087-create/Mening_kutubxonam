
from pydantic import BaseModel, Field


class BookAnalysisDTO(BaseModel):
    summary: str = Field(description="Short synopsis of the book")
    key_ideas: list[str] = Field(default_factory=list, description="Core themes and central thoughts")
    lessons: list[str] = Field(default_factory=list, description="Actionable or philosophical takeaways")
    target_audience: str = Field(description="Who will benefit most from reading this book")
    similar_books: list[str] = Field(default_factory=list, description="Recommended similar titles")
    provider: str = Field(default="metadata", description="gemini | openai | metadata")
    model: str = Field(default="heuristic")
