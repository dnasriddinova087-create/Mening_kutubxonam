import asyncio
import getpass
import sys

from app.core.security import hash_password
from app.database.repositories.admin_repo import AdminRepository
from app.database.session import AsyncSessionLocal, init_db


async def main():
    await init_db()

    print("\n==========================================")
    print(" KITOBXON AI — Administrator yaratish")
    print("==========================================\n")

    if len(sys.argv) >= 3:
        username = sys.argv[1].strip()
        password = sys.argv[2].strip()
    else:
        username = input("Administrator login (username): ").strip()
        if not username:
            print("Xato: Login bo'sh bo'lishi mumkin emas!")
            return
        password = getpass.getpass("Administrator paroli: ").strip()
        if not password:
            print("Xato: Parol bo'sh bo'lishi mumkin emas!")
            return

    async with AsyncSessionLocal() as session:
        repo = AdminRepository(session)
        existing = await repo.get_by_username(username)

        pwd_hash = hash_password(password)

        if existing:
            existing.password_hash = pwd_hash
            existing.is_active = True
            await session.commit()
            print(f"\n[OK] '{username}' administrator paroli muvaffaqiyatli yangilandi!")
        else:
            await repo.create_admin(username=username, password_hash=pwd_hash, role="superadmin")
            print(f"\n[OK] '{username}' yangi administratori muvaffaqiyatli yaratildi!")


if __name__ == "__main__":
    asyncio.run(main())
