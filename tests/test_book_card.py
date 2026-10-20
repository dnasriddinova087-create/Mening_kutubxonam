from app.schemas.book import BookDTO
from app.utils.text import (
    clean_html_tags,
    escape_html,
    format_book_caption,
    format_book_details,
    truncate_text,
)


def test_text_helpers():
    # HTML escape
    assert escape_html("Tom & Jerry <123>") == "Tom &amp; Jerry &lt;123&gt;"

    # Clean HTML tags
    dirty = "<p>This is <b>bold</b> &amp; <i>italic</i> text.</p>"
    clean = clean_html_tags(dirty)
    assert clean == "This is bold & italic text."

    # Truncate
    long_text = "The quick brown fox jumps over the lazy dog"
    truncated = truncate_text(long_text, max_length=20)
    assert len(truncated) <= 20
    assert truncated.endswith("...")


def test_book_card_caption_length():
    dto = BookDTO(
        source="google_books",
        source_book_id="test1",
        title="Very Long Title " * 10,
        authors=["Author One", "Author Two"],
        description="A " * 2000,  # Huge description
        published_date="2020",
        genres=["Science Fiction"],
        access_type="free",
    )

    caption_uz = format_book_caption(dto, lang="uz")
    assert len(caption_uz) <= 1024
    assert "kitob haqida" in caption_uz.lower() or "📚" in caption_uz

    caption_ru = format_book_caption(dto, lang="ru")
    assert len(caption_ru) <= 1024
    assert "о книге" in caption_ru.lower()

    caption_en = format_book_caption(dto, lang="en")
    assert len(caption_en) <= 1024
    assert "about the book" in caption_en.lower()


def test_book_details():
    dto = BookDTO(
        source="local",
        source_book_id="loc1",
        title="O'tkan kunlar",
        authors=["Abdulla Qodiriy"],
        description="Otabek va Kumushning fojiali sevgisi.",
        isbn="9789943001234",
    )
    details = format_book_details(dto, lang="uz")
    assert "Abdulla Qodiriy" in details
    assert "9789943001234" in details
