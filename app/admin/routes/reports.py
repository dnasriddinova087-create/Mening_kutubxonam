from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.dependencies import AdminRole, get_current_admin, require_roles
from app.database.models import Admin
from app.database.repositories.admin_repo import AdminRepository
from app.database.session import get_db

router = APIRouter(prefix="/admin/reports", tags=["admin_reports"])
templates = Jinja2Templates(directory="app/admin/templates")


@router.get("", response_class=HTMLResponse)
async def list_reports_page(
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    admin_repo = AdminRepository(session)
    reports = await admin_repo.list_reports(limit=50)

    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "admin": admin,
            "active_tab": "reports",
            "reports": reports,
        },
    )


@router.post("/{report_id}/resolve")
async def resolve_report_submit(
    report_id: int,
    admin: Admin = Depends(require_roles(AdminRole.SUPPORT, AdminRole.BOOK_MANAGER, AdminRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    admin_repo = AdminRepository(session)
    await admin_repo.resolve_report(report_id)
    await admin_repo.log_audit(
        admin_id=admin.id,
        action="resolve_report",
        target_type="report",
        target_id=str(report_id),
    )
    return RedirectResponse(url="/admin/reports", status_code=status.HTTP_303_SEE_OTHER)
