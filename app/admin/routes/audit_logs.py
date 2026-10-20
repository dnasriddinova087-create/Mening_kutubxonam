from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.dependencies import AdminRole, require_roles
from app.database.models import Admin
from app.database.repositories.admin_repo import AdminRepository
from app.database.session import get_db

router = APIRouter(prefix="/admin/audit-logs", tags=["admin_audit_logs"])
templates = Jinja2Templates(directory="app/admin/templates")


@router.get("", response_class=HTMLResponse)
async def list_audit_logs_page(
    request: Request,
    limit: int = 100,
    admin: Admin = Depends(require_roles(AdminRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    admin_repo = AdminRepository(session)
    logs = await admin_repo.get_audit_logs(limit=limit)

    return templates.TemplateResponse(
        request=request,
        name="audit_logs.html",
        context={
            "admin": admin,
            "active_tab": "audit_logs",
            "logs": logs,
        },
    )
