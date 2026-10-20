import asyncio

from app.database.repositories.book_repo import BookRepository
from app.database.session import AsyncSessionLocal, init_db
from app.schemas.book import BookDTO
from app.services.recommendations import CURATED_RECOMMENDATIONS


async def seed():
    await init_db()
    print("Mahalliy kitoblar katalogi to'ldirilmoqda...")

    async with AsyncSessionLocal() as session:
        repo = BookRepository(session)
        count = 0
        for item in CURATED_RECOMMENDATIONS:
            dto = BookDTO(**item)
            await repo.upsert_from_dto(dto)
            count += 1
            print(f" -> '{dto.title}' qo'shildi.")

    print(f"\n[OK] Jami {count} ta durdona asar muvaffaqiyatli saqlandi!")


if __name__ == "__main__":
    asyncio.run(seed())
