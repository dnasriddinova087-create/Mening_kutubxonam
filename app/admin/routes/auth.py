from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.database.repositories.admin_repo import AdminRepository
from app.database.session import get_db

router = APIRouter(prefix="/admin", tags=["admin_auth"])
templates = Jinja2Templates(directory="app/admin/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="login.html", context={"admin": None, "error": None}
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    admin_repo = AdminRepository(session)
    admin = await admin_repo.get_by_username(username.strip())

    if not admin or not verify_password(password, admin.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "admin": None,
                "error": "Noto'g'ri foydalanuvchi nomi yoki parol!",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if not admin.is_active:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "admin": None,
                "error": "Ushbu administrator hisobi faol emas!",
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # Create session JWT
    token = create_access_token({"sub": admin.username, "role": admin.role})
    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="admin_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )

    await admin_repo.log_audit(
        admin_id=admin.id,
        action="login",
        target_type="admin",
        target_id=str(admin.id),
        details={"ip": request.client.host if request.client else "unknown"},
    )
    return response


@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="admin_token")
    return response
