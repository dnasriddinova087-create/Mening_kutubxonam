from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.dependencies import AdminRole, require_roles
from app.core.security import get_password_hash
from app.database.models import Admin
from app.database.repositories.admin_repo import AdminRepository
from app.database.session import get_db

router = APIRouter(prefix="/admin/admins", tags=["admin_management"])
templates = Jinja2Templates(directory="app/admin/templates")


@router.get("", response_class=HTMLResponse)
async def list_admins_page(
    request: Request,
    admin: Admin = Depends(require_roles(AdminRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    admin_repo = AdminRepository(session)
    admins_list = await admin_repo.list_admins()
    error = request.query_params.get("error")
    success = request.query_params.get("success")

    return templates.TemplateResponse(
        request=request,
        name="admins.html",
        context={
            "admin": admin,
            "active_tab": "admins",
            "admins": admins_list,
            "error": error,
            "success": success,
        },
    )


@router.post("/new")
async def create_admin_submit(
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    admin: Admin = Depends(require_roles(AdminRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    admin_repo = AdminRepository(session)
    clean_user = username.strip()

    if len(clean_user) < 3 or len(password) < 6:
        return RedirectResponse(
            url="/admin/admins?error=Foydalanuvchi+nomi+yoki+parol+juda+qisqa",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    existing = await admin_repo.get_by_username(clean_user)
    if existing:
        return RedirectResponse(
            url="/admin/admins?error=Ushbu+foydalanuvchi+nomi+allaqachon+mavjud",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    pwd_hash = get_password_hash(password)
    created = await admin_repo.create_admin(clean_user, pwd_hash, role)

    await admin_repo.log_audit(
        admin_id=admin.id,
        action="create_admin",
        target_type="admin",
        target_id=str(created.id),
        details={"username": clean_user, "role": role},
    )

    return RedirectResponse(
        url="/admin/admins?success=Yangi+admin+muvaffaqiyatli+yaratildi",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{target_admin_id}/role")
async def update_admin_role_submit(
    target_admin_id: int,
    role: str = Form(...),
    admin: Admin = Depends(require_roles(AdminRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    admin_repo = AdminRepository(session)
    await admin_repo.update_admin_role(target_admin_id, role)

    await admin_repo.log_audit(
        admin_id=admin.id,
        action="update_admin_role",
        target_type="admin",
        target_id=str(target_admin_id),
        details={"new_role": role},
    )

    return RedirectResponse(
        url="/admin/admins?success=Rol+muvaffaqiyatli+yangilandi",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{target_admin_id}/toggle-active")
async def toggle_admin_active_submit(
    target_admin_id: int,
    admin: Admin = Depends(require_roles(AdminRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    if target_admin_id == admin.id:
        return RedirectResponse(
            url="/admin/admins?error=O'zingizning+hisobingizni+faolsizlantira+olmaysiz",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    stmt = update(Admin).where(Admin.id == target_admin_id).values(is_active=~Admin.is_active)
    await session.execute(stmt)
    await session.commit()

    admin_repo = AdminRepository(session)
    await admin_repo.log_audit(
        admin_id=admin.id,
        action="toggle_admin_active",
        target_type="admin",
        target_id=str(target_admin_id),
    )

    return RedirectResponse(
        url="/admin/admins?success=Holat+yangilandi",
        status_code=status.HTTP_303_SEE_OTHER,
    )
