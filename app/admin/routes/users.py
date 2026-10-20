
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.dependencies import get_current_admin
from app.database.models import Admin
from app.database.repositories.admin_repo import AdminRepository
from app.database.repositories.user_repo import UserRepository
from app.database.session import get_db

router = APIRouter(prefix="/admin/users", tags=["admin_users"])
templates = Jinja2Templates(directory="app/admin/templates")


@router.get("", response_class=HTMLResponse)
async def list_users_page(
    request: Request,
    q: str | None = None,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    repo = UserRepository(session)
    users, _ = await repo.get_users_list(offset=0, limit=50, search=q.strip() if q else None)

    return templates.TemplateResponse(
        request=request,
        name="users.html",
        context={
            "admin": admin,
            "active_tab": "users",
            "users": users,
            "search_query": q,
        },
    )


@router.post("/{telegram_id}/toggle-block")
async def toggle_block_user(
    telegram_id: int,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    user_repo = UserRepository(session)
    admin_repo = AdminRepository(session)

    user = await user_repo.get_by_telegram_id(telegram_id)
    if user:
        new_blocked = not user.is_blocked
        await user_repo.set_blocked(telegram_id, new_blocked)
        await admin_repo.log_audit(
            admin_id=admin.id,
            action="block_user" if new_blocked else "unblock_user",
            target_type="user",
            target_id=str(telegram_id),
        )

    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)
