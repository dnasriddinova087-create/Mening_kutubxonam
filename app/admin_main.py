import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select

from app.admin.routes import (
    admins,
    api,
    audit_logs,
    auth,
    books,
    dashboard,
    reports,
    settings,
    users,
)
from app.core.config import settings as app_settings
from app.core.logging import logger, setup_logging
from app.core.security import hash_password
from app.database.models import Book
from app.database.repositories.admin_repo import AdminRepository
from app.database.repositories.book_repo import BookRepository
from app.database.session import AsyncSessionLocal, init_db
from app.schemas.book import BookDTO
from app.services.recommendations import CURATED_RECOMMENDATIONS


async def ensure_bootstrap_data() -> None:
    """Ensure initial books and superadmin user exist on startup."""
    try:
        async with AsyncSessionLocal() as session:
            # 1. Admin user
            admin_repo = AdminRepository(session)
            existing_admins = await admin_repo.list_admins()
            if not existing_admins:
                username = app_settings.DEFAULT_ADMIN_USER
                password = app_settings.DEFAULT_ADMIN_PASSWORD
                pwd_hash = hash_password(password)
                await admin_repo.create_admin(username=username, password_hash=pwd_hash, role="superadmin")
                logger.info(f"Default superadmin created: '{username}' (password: '{password}')")

            # 2. Curated books seed
            if app_settings.AUTO_SEED:
                book_repo = BookRepository(session)
                count_stmt = select(func.count(Book.id))
                book_count = (await session.execute(count_stmt)).scalar() or 0
                if book_count == 0:
                    logger.info("Empty database detected. Seeding curated books catalogue...")
                    for item in CURATED_RECOMMENDATIONS:
                        dto = BookDTO(**item)
                        await book_repo.upsert_from_dto(dto)
                    logger.info(f"Successfully seeded {len(CURATED_RECOMMENDATIONS)} books.")
    except Exception as e:
        logger.warning(f"Bootstrap data check note: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Initializing Admin API & Web Panel...")
    await init_db()
    await ensure_bootstrap_data()

    bot_task = None
    if app_settings.BOT_TOKEN:
        logger.info("BOT_TOKEN detected. Starting Telegram Bot in background...")
        from app.main import run_bot

        async def _safe_bot_run():
            try:
                await run_bot()
            except asyncio.CancelledError:
                logger.info("Telegram Bot task cancelled.")
            except Exception as e:
                logger.error(f"Telegram Bot error: {e}", exc_info=True)

        bot_task = asyncio.create_task(_safe_bot_run())
    else:
        logger.warning("BOT_TOKEN is not configured! Admin panel is running, but Telegram Bot is inactive.")

    yield

    if bot_task and not bot_task.done():
        logger.info("Stopping Telegram Bot background worker...")
        bot_task.cancel()
        try:
            await asyncio.wait_for(bot_task, timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass

    logger.info("Admin Web Panel shutting down...")


app = FastAPI(
    title="KITOBXON AI — Admin Panel",
    description="Professional Administration Panel for Kitobxon AI Book Discovery Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount Static Files
app.mount("/admin/static", StaticFiles(directory="app/admin/static"), name="static")

# Include Routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(books.router)
app.include_router(users.router)
app.include_router(reports.router)
app.include_router(settings.router)
app.include_router(audit_logs.router)
app.include_router(admins.router)
app.include_router(api.router)


@app.get("/")
@app.get("/admin")
async def root():
    return RedirectResponse(url="/admin/dashboard")


if __name__ == "__main__":
    uvicorn.run(
        "app.admin_main:app",
        host=app_settings.ADMIN_HOST,
        port=app_settings.effective_admin_port,
        reload=False,
    )

