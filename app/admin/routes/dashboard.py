from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.dependencies import get_current_admin
from app.database.models import Admin
from app.database.repositories.admin_repo import AdminRepository
from app.database.repositories.search_history_repo import SearchHistoryRepository
from app.database.session import get_db

router = APIRouter(prefix="/admin", tags=["admin_dashboard"])
templates = Jinja2Templates(directory="app/admin/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    admin_repo = AdminRepository(session)
    search_repo = SearchHistoryRepository(session)

    stats = await admin_repo.get_dashboard_stats()
    top_queries = await search_repo.get_top_queries(limit=10)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "admin": admin,
            "active_tab": "dashboard",
            "stats": stats,
            "top_queries": top_queries,
        },
    )
