import pytest

from app.bot.handlers.catalog import format_book_caption
from app.bot.keyboards.inline import get_catalog_control_keyboard
from app.bot.keyboards.reply import get_main_menu_keyboard
from app.core.i18n import t
from app.database.models import Book
from app.database.repositories.book_repo import BookRepository
from app.schemas.book import BookDTO


@pytest.mark.asyncio
async def test_catalog_menu_buttons_i18n():
    """Verify main menu has catalog button across all languages."""
    for lang, expected_text in [
        ("uz", "📚 Barcha kitoblar katalogi"),
        ("ru", "📚 Каталог всех книг"),
        ("en", "📚 All Books Catalog"),
    ]:
        kb = get_main_menu_keyboard(lang)
        all_btn_texts = [btn.text for row in kb.keyboard for btn in row]
        assert expected_text in all_btn_texts, f"Catalog button missing for lang {lang}"


@pytest.mark.asyncio
async def test_catalog_i18n_keys():
    """Verify all required catalog translation keys are present."""
    required_keys = [
        "menu.catalog",
        "catalog.title",
        "catalog.page_header",
        "catalog.open_book",
        "catalog.prev_btn",
        "catalog.next_btn",
        "catalog.empty",
        "catalog.no_cover",
        "catalog.filter_all",
        "catalog.filter_uz",
        "catalog.filter_ru",
        "catalog.filter_en",
        "catalog.reset_filters",
    ]
    for lang in ["uz", "ru", "en"]:
        for key in required_keys:
            val = t(lang, key)
            assert val != key, f"Missing translation for key '{key}' in lang '{lang}'"


@pytest.mark.asyncio
async def test_catalog_control_keyboard():
    """Test catalog control keyboard pagination and filter buttons."""
    # Page 1 of 3
    kb1 = get_catalog_control_keyboard(
        page=1, total_pages=3, current_lang="uz", current_genre="all", lang="uz"
    )
    # Row 0: prev/counter/next
    assert len(kb1.inline_keyboard) >= 4
    nav_row = kb1.inline_keyboard[0]
    assert len(nav_row) == 2  # No prev on page 1, has counter and next
    assert nav_row[0].text == "📄 1 / 3"
    assert "cat:page:2:uz:all" in nav_row[1].callback_data

    # Page 2 of 3
    kb2 = get_catalog_control_keyboard(
        page=2, total_pages=3, current_lang="all", current_genre="all", lang="uz"
    )
    nav_row2 = kb2.inline_keyboard[0]
    assert len(nav_row2) == 3  # Prev, counter, next
    assert "cat:page:1:all:all" in nav_row2[0].callback_data
    assert "cat:page:3:all:all" in nav_row2[2].callback_data

    # Check active filter checkmark
    lang_row = kb1.inline_keyboard[1]
    active_uz_btn = next((b for b in lang_row if "cat:lang:uz:" in b.callback_data), None)
    assert active_uz_btn is not None
    assert "✅" in active_uz_btn.text


@pytest.mark.asyncio
async def test_format_book_caption():
    """Verify book caption formatting and length protection."""
    book = Book(
        id=42,
        original_title="O'tkan kunlar",
        authors=["Abdulla Qodiriy"],
        language="uz",
        genres=["Tarixiy", "Klassika"],
        access_type="free",
        description="A" * 2000,  # Deliberately long description
    )
    caption = format_book_caption(book, "uz")
    assert ("O'tkan kunlar" in caption or "O&#x27;tkan kunlar" in caption)
    assert "Abdulla Qodiriy" in caption
    assert "UZ" in caption
    assert len(caption) <= 1024


@pytest.mark.asyncio
async def test_book_repository_catalog_filtering(db_session):
    """Test BookRepository list_books with pagination, language and genre filters."""
    repo = BookRepository(db_session)

    # Insert test books
    b1 = BookDTO(
        title="O'tkan kunlar",
        authors=["Abdulla Qodiriy"],
        language="uz",
        genres=["Tarixiy", "Klassika"],
        source="local",
        source_book_id="seed_1",
    )
    b2 = BookDTO(
        title="1984",
        authors=["George Orwell"],
        language="en",
        genres=["Dystopia", "Classics"],
        source="local",
        source_book_id="seed_2",
    )
    b3 = BookDTO(
        title="Война и мир",
        authors=["Лев Толстой"],
        language="ru",
        genres=["Tarixiy", "Классика"],
        source="local",
        source_book_id="seed_3",
    )
    await repo.upsert_from_dto(b1)
    await repo.upsert_from_dto(b2)
    await repo.upsert_from_dto(b3)

    # 1. All books
    books, total = await repo.list_books(offset=0, limit=10)
    assert total == 3
    assert len(books) == 3

    # 2. Filter by language 'uz'
    uz_books, uz_total = await repo.list_books(offset=0, limit=10, language="uz")
    assert uz_total == 1
    assert uz_books[0].original_title == "O'tkan kunlar"

    # 3. Filter by language 'en'
    en_books, en_total = await repo.list_books(offset=0, limit=10, language="en")
    assert en_total == 1
    assert en_books[0].original_title == "1984"

    # 4. Filter by genre 'tarixiy'
    tarixiy_books, tarixiy_total = await repo.list_books(offset=0, limit=10, genre="tarixiy")
    assert tarixiy_total == 2  # b1 and b3 have 'Tarixiy'

    # 5. Pagination (limit 2, offset 0 -> 2 books; offset 2 -> 1 book)
    p1_books, _ = await repo.list_books(offset=0, limit=2)
    assert len(p1_books) == 2
    p2_books, _ = await repo.list_books(offset=2, limit=2)
    assert len(p2_books) == 1


@pytest.mark.asyncio
async def test_book_sequential_codes(db_session):
    """Test auto-incrementing sequential book code generation and retrieval."""
    repo = BookRepository(db_session)

    b1 = BookDTO(title="Kitob Bir", authors=["Muallif"], source="local", source_book_id="s_1")
    b2 = BookDTO(title="Kitob Ikki", authors=["Muallif"], source="local", source_book_id="s_2")

    book1 = await repo.upsert_from_dto(b1)
    book2 = await repo.upsert_from_dto(b2)

    assert book1.code is not None
    assert book2.code is not None
    assert book2.code > book1.code

    # Retrieval by code
    found = await repo.get_by_code(book1.code)
    assert found is not None
    assert found.original_title == "Kitob Bir"

    not_found = await repo.get_by_code(999999)
    assert not_found is None


@pytest.mark.asyncio
async def test_catalog_grid_keyboard():
    """Test grid keyboard generation matching serial/movie bot style."""
    from app.bot.keyboards.inline import get_catalog_grid_keyboard

    mock_books = [
        Book(id=1, code=1, original_title="O'tkan kunlar"),
        Book(id=2, code=2, original_title="Mehrobdan chayon"),
        Book(id=3, code=3, original_title="Yulduzli tunlar"),
    ]
    kb = get_catalog_grid_keyboard(books=mock_books, page=1, total_pages=2, lang="uz")

    # Has search buttons row at top
    assert any("cat:search" in btn.callback_data for btn in kb.inline_keyboard[0])
    assert any("cat:code_prompt" in btn.callback_data for btn in kb.inline_keyboard[0])

    # Has book buttons
    all_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "book:view:1" in all_callbacks
    assert "book:view:2" in all_callbacks
    assert "book:view:3" in all_callbacks


@pytest.mark.asyncio
async def test_admin_authorization():
    """Test admin check for Super Admin user ID 8154138330."""
    from app.bot.handlers.admin import is_admin
    from app.core.config import settings

    assert 8154138330 in settings.ADMIN_TELEGRAM_IDS
    assert is_admin(8154138330) is True
    assert is_admin(123456789) is False

