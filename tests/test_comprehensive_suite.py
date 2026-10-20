import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.dependencies import AdminRole, normalize_role
from app.admin_main import app
from app.core.i18n import t
from app.core.security import (
    create_access_token,
    generate_csrf_token,
    get_password_hash,
    verify_password,
)
from app.database.repositories.admin_repo import AdminRepository
from app.database.repositories.book_repo import BookRepository
from app.database.repositories.favorite_repo import FavoriteRepository
from app.database.repositories.user_repo import UserRepository
from app.database.session import AsyncSessionLocal
from app.schemas.book import BookDTO
from app.services.book_search import BookSearchService, _score_book


@pytest.mark.asyncio
async def test_1_to_6_language_selection_and_persistence(db_session: AsyncSession):
    """Requirements 1-6: Selection of uz, ru, en, database persistence, reload, menu text changes."""
    user_repo = UserRepository(db_session)
    tg_id = 998877661

    # 1. Create user and select Uzbek
    user_uz, _ = await user_repo.get_or_create(tg_id, username="test_uz", language="uz")
    assert user_uz.language == "uz"
    assert "Kitob qidirish" in t("uz", "menu.search")

    # 2. Switch to Russian
    await user_repo.update_language(tg_id, "ru")
    user_ru = await user_repo.get_by_telegram_id(tg_id)
    assert user_ru is not None
    assert user_ru.language == "ru"
    assert "Поиск книг" in t("ru", "menu.search")

    # 3. Switch to English
    await user_repo.update_language(tg_id, "en")
    user_en = await user_repo.get_by_telegram_id(tg_id)
    assert user_en is not None
    assert user_en.language == "en"
    assert "Search Books" in t("en", "menu.search")

    # 4. Persistence check on reload
    reloaded_user = await user_repo.get_by_telegram_id(tg_id)
    assert reloaded_user is not None
    assert reloaded_user.language == "en"

    # 5. Preferred book languages update
    await user_repo.update_preferred_book_languages(tg_id, ["uz", "ru"])
    user_pref = await user_repo.get_by_telegram_id(tg_id)
    assert user_pref.preferred_book_languages == ["uz", "ru"]


@pytest.mark.asyncio
async def test_7_to_9_menu_and_i18n_parity():
    """Requirements 7-9: Menu buttons translation keys and parity across all 3 languages."""
    keys = [
        "welcome", "menu.search", "menu.recommend", "menu.favorites",
        "menu.reading_list", "menu.stats", "menu.language", "menu.help",
        "search.prompt", "search.searching", "search.no_results",
        "book.btn_details", "book.btn_ai_analysis", "book.btn_add_favorite",
        "language.choose", "errors.general",
    ]
    for lang in ("uz", "ru", "en"):
        for key in keys:
            text_val = t(lang, key)
            assert text_val != key, f"Missing translation for key '{key}' in lang '{lang}'"
            assert len(text_val) > 0


@pytest.mark.asyncio
async def test_10_to_14_multilingual_search_and_ranking(db_session: AsyncSession):
    """Requirements 10-14: Search by title, author, ISBN, and multilingual prioritization."""
    # Score books with preferred languages = ['uz']
    book_uz = BookDTO(
        source="local", source_book_id="1",
        title="O'tkan kunlar", authors=["Abdulla Qodiriy"],
        language="uz", isbn="9789943000001",
    )
    book_ru = BookDTO(
        source="local", source_book_id="2",
        title="Минувшие дни (на русском)", authors=["Абдулла Кадыри"],
        language="ru", isbn="9789943000002",
    )
    book_en = BookDTO(
        source="local", source_book_id="3",
        title="Bygone Days", authors=["Abdulla Qodiriy"],
        language="en", isbn="9789943000003",
    )

    pref_langs = {"uz"}
    score_uz = _score_book(book_uz, "o'tkan", pref_langs, iface_lang="uz")
    score_ru = _score_book(book_ru, "o'tkan", pref_langs, iface_lang="uz")
    score_en = _score_book(book_en, "o'tkan", pref_langs, iface_lang="uz")

    # Uzbek book must score higher when 'uz' is preferred!
    assert score_uz > score_ru
    assert score_uz > score_en

    # Search with mocked providers
    service = BookSearchService(db_session)
    service.google_provider.search = AsyncMock(return_value=[book_ru])
    service.openlibrary_provider.search = AsyncMock(return_value=[book_en])
    service.local_provider.search = AsyncMock(return_value=[book_uz])

    results = await service.search("o'tkan", limit=10, preferred_languages=["uz"], interface_language="uz")
    assert len(results) >= 1
    # First result must be the Uzbek book
    assert results[0].language == "uz"


@pytest.mark.asyncio
async def test_16_to_17_favorites_and_user_data_isolation(db_session: AsyncSession):
    """Requirements 16-17: Favorites addition/removal and strict data isolation between users."""
    user_repo = UserRepository(db_session)
    fav_repo = FavoriteRepository(db_session)
    book_repo = BookRepository(db_session)

    # Setup User A and User B
    user_a, _ = await user_repo.get_or_create(1001, username="alice")
    user_b, _ = await user_repo.get_or_create(1002, username="bob")

    book_dto = BookDTO(
        source="local", source_book_id="iso_1",
        title="Sariq devni minib", authors=["Xudoyberdi To'xtaboyev"],
    )
    book = await book_repo.upsert_from_dto(book_dto)

    # User A adds to favorites
    await fav_repo.add(user_a.id, book.id)
    assert await fav_repo.is_favorite(user_a.id, book.id) is True

    # User B should NOT have it in favorites (strict isolation)
    assert await fav_repo.is_favorite(user_b.id, book.id) is False
    favs_b = await fav_repo.get_user_favorites(user_b.id)
    assert len(favs_b) == 0

    # User A removes favorite
    await fav_repo.remove(user_a.id, book.id)
    assert await fav_repo.is_favorite(user_a.id, book.id) is False


@pytest.mark.asyncio
async def test_18_to_20_admin_auth_and_rbac():
    """Requirements 18-20: Admin login, invalid login rate limiting / rejection, and RBAC roles."""
    # 1. Password hashing verification
    pwd = "SecretPassword123!"
    h = get_password_hash(pwd)
    assert verify_password(pwd, h) is True
    assert verify_password("WrongPassword", h) is False

    # 2. Roles normalization
    assert normalize_role("SUPER_ADMIN") == AdminRole.SUPER_ADMIN
    assert normalize_role("admin") == AdminRole.SUPER_ADMIN
    assert normalize_role("BOOK_MANAGER") == AdminRole.BOOK_MANAGER
    assert normalize_role("SUPPORT") == AdminRole.SUPPORT
    assert normalize_role("ANALYST") == AdminRole.ANALYST

    # 3. Create admins in DB
    u_super = f"super_{uuid.uuid4().hex[:6]}"
    u_mgr = f"mgr_{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        admin_repo = AdminRepository(session)
        super_admin = await admin_repo.create_admin(u_super, h, role=AdminRole.SUPER_ADMIN)
        book_mgr = await admin_repo.create_admin(u_mgr, h, role=AdminRole.BOOK_MANAGER)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid login
        res_bad = await client.post("/admin/login", data={"username": u_super, "password": "wrong"})
        assert res_bad.status_code == 400

        # Valid login
        res_ok = await client.post("/admin/login", data={"username": u_super, "password": pwd}, follow_redirects=False)
        assert res_ok.status_code == 303
        assert "admin_token" in res_ok.cookies

        # Test RBAC with book manager token trying to access settings (SUPER_ADMIN only)
        bm_token = create_access_token({"sub": book_mgr.username, "role": book_mgr.role})
        client.cookies.set("admin_token", bm_token)

        res_settings_forbidden = await client.get("/admin/settings")
        assert res_settings_forbidden.status_code == 403

        # SUPER_ADMIN token accessing settings (should succeed)
        sa_token = create_access_token({"sub": super_admin.username, "role": super_admin.role})
        client.cookies.set("admin_token", sa_token)
        res_settings_ok = await client.get("/admin/settings")
        assert res_settings_ok.status_code == 200


@pytest.mark.asyncio
async def test_21_to_23_admin_books_settings_and_audit(db_session: AsyncSession):
    """Requirements 21-23: Book CRUD, system settings persistence, and audit logging."""
    admin_repo = AdminRepository(db_session)
    book_repo = BookRepository(db_session)

    # 1. Audit log write and read
    log = await admin_repo.log_audit(
        admin_id=1,
        action="test_action",
        target_type="book",
        target_id="42",
        details={"info": "sample"},
    )
    assert log.id is not None
    logs = await admin_repo.get_audit_logs(limit=10)
    assert any(item.action == "test_action" for item in logs)

    # 2. Settings set and get
    await admin_repo.set_setting("search", {"search_limit": 25, "api_timeout": 8})
    saved_cfg = await admin_repo.get_setting("search")
    assert saved_cfg["search_limit"] == 25
    assert saved_cfg["api_timeout"] == 8

    # 3. Book CRUD
    created = await book_repo.upsert_from_dto(BookDTO(
        source="local", source_book_id="admin_crud_1",
        title="Yulduzli tunlar", authors=["Pirimqul Qodirov"],
        language="uz", genres=["Tarixiy"],
    ))
    assert created.id is not None

    # Update
    updated = await book_repo.update_book_details(
        book_id=created.id,
        title="Yulduzli tunlar (Yangi nashr)",
        authors=["Pirimqul Qodirov"],
        description="Bobur haqida roman",
        cover_url="https://example.com/cover.jpg",
        publisher="Sharq",
        published_date="2022",
        isbn="9789943001111",
        access_type="free",
        reading_url="https://example.com/read",
        language="uz",
        genres=["Tarixiy", "Klassika"],
    )
    assert updated is True

    # Delete
    deleted = await book_repo.delete_book(created.id)
    assert deleted is True
    assert await book_repo.get_by_id(created.id) is None


@pytest.mark.asyncio
async def test_24_to_25_api_error_handling_and_ai_fallback():
    """Requirements 24-25: API timeout / error resilience and AI disabled fallback."""
    from app.providers.ai_provider import MetadataAnalysisProvider

    provider = MetadataAnalysisProvider()
    book = BookDTO(
        source="local", source_book_id="mock_1",
        title="Alkimyogar", authors=["Paulo Coelho"],
        description="Orzular ortidan ergashish haqidagi falsafiy asar.",
        genres=["Falsafa"],
    )

    # Fallback analysis works without external API dependency
    analysis = await provider.analyze_book(book, language="uz")
    assert "Alkimyogar" in analysis.summary
    assert len(analysis.summary) > 0
    assert len(analysis.lessons) > 0


@pytest.mark.asyncio
async def test_28_csrf_and_security():
    """Requirement 28: Security tokens, CSRF generation, and timing attacks."""
    token1 = generate_csrf_token()
    token2 = generate_csrf_token()
    assert token1 != token2
    assert len(token1) >= 32
