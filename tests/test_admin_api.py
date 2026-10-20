import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.admin_main import app
from app.core.security import hash_password
from app.database.models import Base
from app.database.repositories.admin_repo import AdminRepository
from app.database.session import AsyncSessionLocal, engine


@pytest.mark.asyncio
async def test_admin_api_endpoints():
    test_user = f"admin_{uuid.uuid4().hex[:6]}"

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create admin user
    async with AsyncSessionLocal() as session:
        admin_repo = AdminRepository(session)
        await admin_repo.create_admin(
            username=test_user,
            password_hash=hash_password("adminpass123"),
            role="superadmin",
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check
        resp = await client.get("/admin/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # 2. Protected endpoint without token -> redirect or 401
        resp = await client.get("/admin/dashboard", follow_redirects=False)
        assert resp.status_code in (302, 303, 307)
        assert "/admin/login" in resp.headers.get("location", "")

        # 3. Login attempt with wrong password
        login_fail = await client.post(
            "/admin/login",
            data={"username": test_user, "password": "wrongpassword"},
        )
        assert login_fail.status_code == 400

        # 4. Login attempt with correct password
        login_success = await client.post(
            "/admin/login",
            data={"username": test_user, "password": "adminpass123"},
            follow_redirects=False,
        )
        assert login_success.status_code == 303
        assert "admin_token" in login_success.cookies

        # 5. Access dashboard with cookie
        dashboard_resp = await client.get("/admin/dashboard", cookies=login_success.cookies)
        assert dashboard_resp.status_code == 200
        assert test_user in dashboard_resp.text
