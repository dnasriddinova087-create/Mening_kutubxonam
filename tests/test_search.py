import pytest

from app.database.repositories.book_repo import BookRepository
from app.database.repositories.user_repo import UserRepository
from app.schemas.book import BookDTO
from app.services.favorites import FavoritesService
from app.services.reading_list import ReadingListService


@pytest.mark.asyncio
async def test_user_and_book_repositories(db_session):
    user_repo = UserRepository(db_session)
    book_repo = BookRepository(db_session)

    # 1. Create User
    user, created = await user_repo.get_or_create(
        telegram_id=111222333,
        username="testuser",
        full_name="Test User",
        language="uz",
    )
    assert created is True
    assert user.telegram_id == 111222333

    # 2. Add Book
    dto = BookDTO(
        source="local",
        source_book_id="book_1",
        title="Shum bola",
        authors=["G'afur G'ulom"],
        description="Qiziqarli qissa",
        genres=["Qissa", "Bolalar adabiyoti"],
        access_type="free",
    )
    book = await book_repo.upsert_from_dto(dto)
    assert book.id is not None
    assert book.original_title == "Shum bola"

    # Search local
    found, total = await book_repo.search_local("Shum", offset=0, limit=10)
    assert total >= 1
    assert found[0].id == book.id


@pytest.mark.asyncio
async def test_user_data_isolation_and_favorites(db_session):
    user_repo = UserRepository(db_session)
    book_repo = BookRepository(db_session)
    fav_service = FavoritesService(db_session)
    reading_service = ReadingListService(db_session)

    # User 1 & User 2
    u1, _ = await user_repo.get_or_create(telegram_id=1001, username="user1")
    u2, _ = await user_repo.get_or_create(telegram_id=1002, username="user2")

    b1 = await book_repo.upsert_from_dto(
        BookDTO(source="local", source_book_id="b1", title="Book 1", authors=["Author 1"])
    )
    b2 = await book_repo.upsert_from_dto(
        BookDTO(source="local", source_book_id="b2", title="Book 2", authors=["Author 2"])
    )

    # User 1 favorites Book 1
    added = await fav_service.toggle_favorite(u1.id, b1.id)
    assert added is True
    assert await fav_service.is_favorite(u1.id, b1.id) is True

    # User 2 should NOT have Book 1 in favorites (Data Isolation)
    assert await fav_service.is_favorite(u2.id, b1.id) is False

    u1_favs = await fav_service.get_favorites(u1.id)
    assert len(u1_favs) == 1
    assert u1_favs[0].id == b1.id

    u2_favs = await fav_service.get_favorites(u2.id)
    assert len(u2_favs) == 0

    # User 2 adds Book 2 to reading list as reading
    await reading_service.update_status(u2.id, b2.id, "reading")
    u2_reading = await reading_service.get_items(u2.id, status="reading")
    assert len(u2_reading) == 1
    assert u2_reading[0][1].id == b2.id

    # User 1 should have 0 items in reading list
    u1_reading = await reading_service.get_items(u1.id)
    assert len(u1_reading) == 0

    # Toggle favorite off for User 1
    removed = await fav_service.toggle_favorite(u1.id, b1.id)
    assert removed is False
    assert await fav_service.is_favorite(u1.id, b1.id) is False
