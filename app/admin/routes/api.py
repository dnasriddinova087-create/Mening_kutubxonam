from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.dependencies import get_current_admin
from app.database.models import Admin
from app.database.repositories.admin_repo import AdminRepository
from app.database.session import get_db

router = APIRouter(prefix="/admin/api", tags=["admin_api"])


@router.get("/health")
async def health_check():
    return {"status": "ok", "app": "KITOBXON AI Admin API"}


@router.get("/stats")
async def api_stats(
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    admin_repo = AdminRepository(session)
    stats = await admin_repo.get_dashboard_stats()
    return {"status": "success", "data": stats}
