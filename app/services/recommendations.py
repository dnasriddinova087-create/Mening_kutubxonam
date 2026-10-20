
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.book_repo import BookRepository, book_to_dto
from app.schemas.book import BookDTO

# Curated perennial masterpieces across Uzbek, World, and Russian literature
CURATED_RECOMMENDATIONS = [
    {
        "title": "O'tkan kunlar",
        "authors": ["Abdulla Qodiriy"],
        "description": "O'zbek adabiyotining birinchi romani bo'lib, XIX asr o'rtalaridagi Toshkent va Qo'qon xonligi davridagi murakkab ijtimoiy-tarixiy voqealar va Otabek bilan Kumushning fojiali sevgisi haqida hikoya qiladi.",
        "language": "uz",
        "genres": ["Klassika", "Tarixiy roman", "Drama"],
        "source": "local",
        "source_book_id": "curated_otkan_kunlar",
        "access_type": "free",
        "reading_url": "https://ziyouz.com",
    },
    {
        "title": "Mehrobdan chayon",
        "authors": ["Abdulla Qodiriy"],
        "description": "Xudoyorxon davridagi saroy fitnalari, adolat va qabohat o'rtasidagi kurash hamda Anvar va Ra'noning pok muhabbati tasvirlangan tarixiy asar.",
        "language": "uz",
        "genres": ["Klassika", "Tarixiy roman"],
        "source": "local",
        "source_book_id": "curated_mehrobdan_chayon",
        "access_type": "free",
        "reading_url": "https://ziyouz.com",
    },
    {
        "title": "Yulduzli tunlar",
        "authors": ["Pirimqul Qodirov"],
        "description": "Zahiriddin Muhammad Boburning murakkab hayot yo'li, Temuriylar saltanati inqirozi va Hindistonda Boburiylar sulolasining asos solinishi haqidagi yuksak mahorat bilan yozilgan tarixiy roman.",
        "language": "uz",
        "genres": ["Tarixiy roman", "Biografiya"],
        "source": "local",
        "source_book_id": "curated_yulduzli_tunlar",
        "access_type": "free",
        "reading_url": "https://ziyouz.com",
    },
    {
        "title": "1984",
        "authors": ["George Orwell"],
        "description": "Totalitar tuzum, doimiy kuzatuv, erkin fikrning bo'g'ilishi va insoniy tuyg'ularning fojiasi haqida ogohlantiruvchi mashhur distopik asar.",
        "language": "en",
        "genres": ["Dystopia", "Classics", "Political fiction"],
        "source": "local",
        "source_book_id": "curated_1984",
        "access_type": "free",
        "reading_url": "https://www.gutenberg.org",
    },
    {
        "title": "To Kill a Mockingbird",
        "authors": ["Harper Lee"],
        "description": "A gripping, heart-wrenching, and wholly remarkable tale of coming-of-age in a South poisoned by virulent prejudice, viewing a world of great beauty and savage inequities through the eyes of a young girl.",
        "language": "en",
        "genres": ["Classics", "Historical Fiction", "Drama"],
        "source": "local",
        "source_book_id": "curated_mockingbird",
        "access_type": "preview",
    },
    {
        "title": "Война и мир",
        "authors": ["Лев Толстой"],
        "description": "Грандиозный роман-эпопея, описывающий русское общество в эпоху войн против Наполеона в 1805—1812 годах, глубочайшие философские размышления о судьбе, свободе и человеческой душе.",
        "language": "ru",
        "genres": ["Классика", "Исторический роман", "Философия"],
        "source": "local",
        "source_book_id": "curated_war_and_peace",
        "access_type": "free",
        "reading_url": "https://ilibrary.ru",
    },
    {
        "title": "Мастер и Маргарита",
        "authors": ["Михаил Булгаков"],
        "description": "Бессмертный роман о визите Воланда в Москву 1930-х годов, вечной любви Мастера и Маргариты и библейской истории Понтия Пилата и Иешуа Га-Ноцри.",
        "language": "ru",
        "genres": ["Классика", "Мистика", "Философский роман"],
        "source": "local",
        "source_book_id": "curated_master_margarita",
        "access_type": "free",
        "reading_url": "https://ilibrary.ru",
    },
]


class RecommendationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.book_repo = BookRepository(session)

    async def get_recommendations(self, language: str = "uz", limit: int = 5) -> list[BookDTO]:
        """Return curated recommendations matching user language preference and local catalog."""
        # Check if local catalog already has books
        books, _ = await self.book_repo.list_books(offset=0, limit=limit, include_archived=False)
        if len(books) >= 3:
            return [book_to_dto(b) for b in books[:limit]]

        # Seed and return from curated list
        result_dtos: list[BookDTO] = []
        for item in CURATED_RECOMMENDATIONS:
            dto = BookDTO(**item)
            try:
                db_book = await self.book_repo.upsert_from_dto(dto)
                result_dtos.append(book_to_dto(db_book))
            except Exception:
                result_dtos.append(dto)

        # Sort recommendations: matching language first
        result_dtos.sort(key=lambda b: 0 if b.language == language else 1)
        return result_dtos[:limit]
