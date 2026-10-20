from app.schemas.book import BookDTO
from app.services.book_search import BookSearchService


def test_book_dto_deduplication_keys():
    b1 = BookDTO(
        source="google_books",
        source_book_id="g1",
        title="O'tkan kunlar",
        authors=["Abdulla Qodiriy"],
        isbn="978-9943-00-123-4",
    )
    b2 = BookDTO(
        source="open_library",
        source_book_id="ol1",
        title="Otkan kunlar",
        authors=["Abdulla Qodiriy"],
        isbn="9789943001234",
    )
    assert b1.deduplication_key() == b2.deduplication_key()


def test_search_service_deduplication():
    service = BookSearchService(session=None)  # Session not needed for pure logic test

    b1 = BookDTO(
        source="google_books",
        source_book_id="g1",
        title="Atomic Habits",
        authors=["James Clear"],
        isbn="9780735211292",
        description="An Easy & Proven Way to Build Good Habits & Break Bad Ones",
        cover_url=None,
    )
    b2 = BookDTO(
        source="open_library",
        source_book_id="ol1",
        title="Atomic Habits",
        authors=["James Clear"],
        isbn="9780735211292",
        description=None,
        cover_url="https://covers.openlibrary.org/b/id/12345-L.jpg",
    )

    deduped = service._deduplicate([b1, b2])
    assert len(deduped) == 1
    # Check that metadata merged properly
    assert deduped[0].description == b1.description
    assert deduped[0].cover_url == b2.cover_url
