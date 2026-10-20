import asyncio
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.dependencies import AdminRole, require_roles
from app.core.config import settings
from app.database.models import Admin
from app.database.repositories.admin_repo import AdminRepository
from app.database.session import get_db

router = APIRouter(prefix="/admin/settings", tags=["admin_settings"])
templates = Jinja2Templates(directory="app/admin/templates")


async def get_system_health(session: AsyncSession) -> dict[str, Any]:
    health: dict[str, Any] = {
        "db": {"status": "ok", "latency_ms": 0},
        "redis": {"status": "unavailable", "latency_ms": 0},
        "google_books": {"status": "unknown", "latency_ms": 0},
        "open_library": {"status": "unknown", "latency_ms": 0},
    }

    # 1. Database check
    try:
        t0 = time.perf_counter()
        await session.execute(text("SELECT 1"))
        health["db"]["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        health["db"]["status"] = "online"
    except Exception as e:
        health["db"]["status"] = f"error: {str(e)[:30]}"

    # 2. Redis check
    if settings.REDIS_URL:
        try:
            import redis.asyncio as aioredis
            t0 = time.perf_counter()
            r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5)
            await r.ping()
            await r.aclose()
            health["redis"]["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            health["redis"]["status"] = "online"
        except Exception:
            health["redis"]["status"] = "offline (in-memory fallback active)"
    else:
        health["redis"]["status"] = "in-memory (no url configured)"

    # 3. Google Books & Open Library check
    async def check_http(url: str, key: str):
        try:
            t0 = time.perf_counter()
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(url)
                health[key]["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                health[key]["status"] = "online" if res.status_code in (200, 400) else f"HTTP {res.status_code}"
        except Exception:
            health[key]["status"] = "timeout/error"

    await asyncio.gather(
        check_http("https://www.googleapis.com/books/v1/volumes?q=test&maxResults=1", "google_books"),
        check_http("https://openlibrary.org/search.json?q=test&limit=1", "open_library"),
        return_exceptions=True,
    )

    return health


@router.get("", response_class=HTMLResponse)
async def view_settings_page(
    request: Request,
    admin: Admin = Depends(require_roles(AdminRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    admin_repo = AdminRepository(session)
    all_settings = await admin_repo.get_all_settings()
    health = await get_system_health(session)

    # Defaults
    general = all_settings.get("general", {
        "bot_name": "KITOBXON AI",
        "bot_description": "Sun'iy intellekt asosidagi zamonaviy kitob qidiruv platformasi",
        "supported_languages": ["uz", "ru", "en"],
        "default_interface_language": "uz",
        "default_book_language": "uz",
        "timezone": "Asia/Tashkent",
        "support_contact": "@kitobxon_support",
    })

    search_cfg = all_settings.get("search", {
        "search_limit": 15,
        "api_timeout": 10,
        "cache_ttl": 3600,
        "search_rate_limit": 20,
        "language_priority": "strict",
        "fallback_enabled": True,
        "provider_status": "all_active",
    })

    ai_cfg = all_settings.get("ai", {
        "ai_enabled": True,
        "ai_provider": settings.AI_PROVIDER,
        "ai_model": settings.AI_MODEL,
        "daily_limit_per_user": 10,
        "max_response_length": 1500,
        "cache_enabled": True,
    })

    user_cfg = all_settings.get("user", {
        "rate_limit_seconds": 0.5,
        "spam_protection": True,
        "feedback_enabled": True,
        "gdpr_policy": "30_days",
    })

    success_msg = request.query_params.get("success")

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "admin": admin,
            "active_tab": "settings",
            "general": general,
            "search_cfg": search_cfg,
            "ai_cfg": ai_cfg,
            "user_cfg": user_cfg,
            "health": health,
            "success_msg": success_msg,
        },
    )


@router.post("")
async def save_settings_submit(
    request: Request,
    section: str = Form(...),
    admin: Admin = Depends(require_roles(AdminRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    form_data = await request.form()
    admin_repo = AdminRepository(session)

    if section == "general":
        cfg = {
            "bot_name": str(form_data.get("bot_name", "KITOBXON AI")).strip(),
            "bot_description": str(form_data.get("bot_description", "")).strip(),
            "default_interface_language": str(form_data.get("default_interface_language", "uz")),
            "default_book_language": str(form_data.get("default_book_language", "uz")),
            "timezone": str(form_data.get("timezone", "Asia/Tashkent")).strip(),
            "support_contact": str(form_data.get("support_contact", "")).strip(),
            "supported_languages": ["uz", "ru", "en"],
        }
        await admin_repo.set_setting("general", cfg)
    elif section == "search":
        cfg = {
            "search_limit": int(form_data.get("search_limit", 15)),
            "api_timeout": int(form_data.get("api_timeout", 10)),
            "cache_ttl": int(form_data.get("cache_ttl", 3600)),
            "search_rate_limit": int(form_data.get("search_rate_limit", 20)),
            "language_priority": str(form_data.get("language_priority", "strict")),
            "fallback_enabled": form_data.get("fallback_enabled") == "on",
            "provider_status": "all_active",
        }
        await admin_repo.set_setting("search", cfg)
    elif section == "ai":
        cfg = {
            "ai_enabled": form_data.get("ai_enabled") == "on",
            "ai_provider": str(form_data.get("ai_provider", "gemini")),
            "ai_model": str(form_data.get("ai_model", "gemini-1.5-flash")).strip(),
            "daily_limit_per_user": int(form_data.get("daily_limit_per_user", 10)),
            "max_response_length": int(form_data.get("max_response_length", 1500)),
            "cache_enabled": form_data.get("cache_enabled") == "on",
        }
        await admin_repo.set_setting("ai", cfg)
    elif section == "user":
        cfg = {
            "rate_limit_seconds": float(form_data.get("rate_limit_seconds", 0.5)),
            "spam_protection": form_data.get("spam_protection") == "on",
            "feedback_enabled": form_data.get("feedback_enabled") == "on",
            "gdpr_policy": str(form_data.get("gdpr_policy", "30_days")),
        }
        await admin_repo.set_setting("user", cfg)

    await admin_repo.log_audit(
        admin_id=admin.id,
        action="update_settings",
        target_type="setting",
        target_id=section,
        details={"section": section},
    )

    return RedirectResponse(
        url="/admin/settings?success=1",
        status_code=status.HTTP_303_SEE_OTHER,
    )
