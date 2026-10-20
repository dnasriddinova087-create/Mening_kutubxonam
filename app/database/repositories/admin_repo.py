from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Admin, AuditLog, Book, Favorite, Report, SearchHistory, User


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_username(self, username: str) -> Admin | None:
        stmt = select(Admin).where(Admin.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_admin(
        self, username: str, password_hash: str, role: str = "admin"
    ) -> Admin:
        admin = Admin(
            username=username,
            password_hash=password_hash,
            role=role,
            is_active=True,
        )
        self.session.add(admin)
        await self.session.commit()
        await self.session.refresh(admin)
        return admin

    async def log_audit(
        self,
        admin_id: int | None,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        log = AuditLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details_json=details or {},
        )
        self.session.add(log)
        await self.session.commit()
        return log

    async def get_audit_logs(self, limit: int = 50) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()
        return list(items)

    async def get_dashboard_stats(self) -> dict[str, Any]:
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now - timedelta(days=30)

        total_users = (await self.session.execute(select(func.count(User.id)))).scalar() or 0
        registered_today = (
            await self.session.execute(
                select(func.count(User.id)).where(User.created_at >= today_start)
            )
        ).scalar() or 0
        active_today = (
            await self.session.execute(
                select(func.count(User.id)).where(User.last_active_at >= today_start)
            )
        ).scalar() or 0
        active_month = (
            await self.session.execute(
                select(func.count(User.id)).where(User.last_active_at >= month_start)
            )
        ).scalar() or 0

        total_books = (await self.session.execute(select(func.count(Book.id)))).scalar() or 0
        total_searches = (await self.session.execute(select(func.count(SearchHistory.id)))).scalar() or 0
        today_searches = (
            await self.session.execute(
                select(func.count(SearchHistory.id)).where(SearchHistory.created_at >= today_start)
            )
        ).scalar() or 0
        total_favorites = (await self.session.execute(select(func.count(Favorite.id)))).scalar() or 0
        pending_reports = (
            await self.session.execute(
                select(func.count(Report.id)).where(Report.status == "pending")
            )
        ).scalar() or 0

        # Language distribution
        lang_rows = (
            await self.session.execute(
                select(User.language, func.count(User.id)).group_by(User.language)
            )
        ).all()
        lang_stats = {r[0]: r[1] for r in lang_rows}

        return {
            "total_users": total_users,
            "registered_today": registered_today,
            "active_today": active_today,
            "active_month": active_month,
            "total_books": total_books,
            "total_searches": total_searches,
            "today_searches": today_searches,
            "total_favorites": total_favorites,
            "pending_reports": pending_reports,
            "lang_stats": lang_stats,
        }

    async def create_report(
        self, user_id: int, book_id: int | None, report_type: str, message: str
    ) -> Report:
        rep = Report(
            user_id=user_id,
            book_id=book_id,
            report_type=report_type,
            message=message,
            status="pending",
        )
        self.session.add(rep)
        await self.session.commit()
        await self.session.refresh(rep)
        return rep

    async def list_reports(self, status: str | None = None, limit: int = 50) -> list[Report]:
        stmt = select(Report)
        if status:
            stmt = stmt.where(Report.status == status)
        stmt = stmt.order_by(desc(Report.created_at)).limit(limit)
        items = (await self.session.execute(stmt)).scalars().all()
        return list(items)

    async def resolve_report(self, report_id: int) -> bool:
        stmt = (
            update(Report)
            .where(Report.id == report_id)
            .values(status="resolved", resolved_at=datetime.now(UTC))
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount > 0

    async def get_setting(self, key: str, default: Any = None) -> Any:
        from app.database.models import AppSetting
        stmt = select(AppSetting).where(AppSetting.key == key)
        setting = (await self.session.execute(stmt)).scalar_one_or_none()
        if setting and setting.value_json is not None:
            return setting.value_json
        return default

    async def set_setting(self, key: str, value: Any) -> Any:
        from app.database.models import AppSetting
        stmt = select(AppSetting).where(AppSetting.key == key)
        setting = (await self.session.execute(stmt)).scalar_one_or_none()
        val_dict = value if isinstance(value, dict) else {"value": value}
        if setting:
            setting.value_json = val_dict
            setting.updated_at = datetime.now(UTC)
        else:
            setting = AppSetting(key=key, value_json=val_dict)
            self.session.add(setting)
        await self.session.commit()
        return setting.value_json

    async def get_all_settings(self) -> dict[str, Any]:
        from app.database.models import AppSetting
        stmt = select(AppSetting)
        rows = (await self.session.execute(stmt)).scalars().all()
        return {r.key: r.value_json for r in rows}

    async def list_admins(self) -> list[Admin]:
        stmt = select(Admin).order_by(Admin.id.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def update_admin_role(self, admin_id: int, role: str) -> bool:
        stmt = update(Admin).where(Admin.id == admin_id).values(role=role)
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount > 0
