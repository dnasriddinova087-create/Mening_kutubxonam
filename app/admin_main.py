from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

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
from app.database.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Initializing Admin API & Web Panel...")
    await init_db()
    yield
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
        port=app_settings.ADMIN_PORT,
        reload=False,
    )
