# 📚 KITOBXON AI — Professional Telegram Book Discovery Platform

**KITOBXON AI** — Python 3.12, aiogram 3.x, FastAPI, PostgreSQL (SQLAlchemy 2.x Async ORM), Redis va zamonaviy AI provayderlari (Google Gemini / OpenAI) asosida qurilgan professional, xavfsiz va kengaytiriladigan kitob qidiruv hamda kashfiyot platformasi.

---

## 🌟 Asosiy imkoniyatlar

1. **Ko'p manbali kitob qidiruvi**:
   - **Google Books API** (muqova, tavsif, ISBN, preview/reading havolalari).
   - **Open Library Search API** (mualliflar, kutubxonadan qarzga olish, ochiq manbalar).
   - **Mahalliy katalog** (administrator tomonidan tasdiqlangan va tahrirlangan kitoblar).
   - Kitob nomi, muallif ismi yoki familiyasi, ISBN-10/13 yoki nomning bir qismi bo'yicha tezkor qidiruv.
   - Lotin va kirill yozuvlaridagi so'rovlarni avtomatik normallashtirish va transliteratsiya qilish (masalan, *O'tkan kunlar* <-> *Ўткан кунлар*).
   - Takroriy kitoblarni ISBN va muallif+nom bo'yicha aqlli deduplikatsiya qilish.
   - 5 tadan sahifalangan inline natijalar (⬅️ Oldingi / Keyingi ➡️).

2. **Mukammal kitob kartochkasi**:
   - Yuqori sifatli muqova surati (Telegram 1024-belgilik rasm chekloviga to'liq moslangan ixcham caption).
   - To'liq bibliografik tafsilotlar (Muallif, Nashriyot, Yil, Janr, Til, ISBN, Manba).
   - **Qonuniy elektron o'qish manbalari**: Bepul to'liq o'qish (ochiq manba), qisman ko'rish (preview), kutubxonadan qarzga olish (Open Library) yoki rasmiy xarid qilish havolalari.
   - Inline amallar:
     - 📚 *Batafsil ma'lumot*
     - 🧠 *AI tahlili*
     - 🔖 *Sevimlilarga saqlash / O'chirish*
     - 📚 *O'qish ro'yxatiga qo'shish* (O'qimoqchiman / O'qiyapman / O'qib bo'ldim)
     - 📖 *Qonuniy o'qish manbalari*
     - 🔍 *O'xshash kitoblar*
     - ↩️ *Orqaga*

3. **AI tahlil moduli**:
   - Asar qisqacha mazmuni, asosiy g'oyalari, axloqiy/falsafiy saboqlari, kimlarga mosligi va o'xshash kitob tavsiyalari.
   - `AnalysisProvider` adapter arxitekturasi: Google Gemini (`gemini-1.5-flash`), OpenAI yoki kalit bo'lmaganda metama'lumotlar asosida avtomatik ishlaydigan `MetadataAnalysisProvider` fallback.
   - Takroriy so'rovlarni kamaytirish va tezlikni oshirish uchun tahlillar ma'lumotlar bazasida (`book_analyses`) keshlanadi.

4. **Uch tilli to'liq lokalizatsiya**:
   - 🇺🇿 O'zbek tili (`uz`)
   - 🇷🇺 Rus tili (`ru`)
   - 🇬🇧 Ingliz tili (`en`)
   - Barcha menyular, xabarlar, xatolar, tugmalar va yordam matnlari `locales/*.json` orqali boshqariladi. Kod ichida qattiq bog'langan matnlar yo'q.

5. **Foydalanuvchi profili va GDPR xavfsizligi**:
   - Oylik kitobxonlik maqsadi belgilash (masalan: oyiga 5 ta kitob).
   - O'qilgan va o'qilayotgan kitoblar statistikasi.
   - Shaxsiy ma'lumotlarni eksport qilish (JSON formatida).
   - Ma'lumotlarni butunlay o'chirish (Right to be forgotten).
   - Foydalanuvchilar o'rtasida to'liq ma'lumotlar izolyatsiyasi.

6. **FastAPI Administrator Paneli**:
   - Zamonaviy qorong'i rejim (Dark theme) va responsive dizayn.
   - Jonli statistika dashboardi (Foydalanuvchilar, faollar, qidiruvlar, eng ko'p izlangan kitoblar).
   - Mahalliy katalogga yangi kitob qo'shish va tahrirlash.
   - Noto'g'ri kitoblarni arxivlash / yashirish.
   - Foydalanuvchilarni ko'rish va bloklash / blokdan chiqarish.
   - Shikoyatlar va foydalanuvchilar murojaatlarini hal qilish.
   - Xavfsiz PBKDF2 parol xeshlash, JWT sessiya cookie, CSRF va audit jurnallari.

---

## 🏗️ Loyiha tuzilishi

```text
kitobxon-ai/
├── app/
│   ├── admin/               # FastAPI Admin paneli (routes, templates, static)
│   ├── bot/                 # aiogram 3 Telegram Bot (handlers, keyboards, middlewares, states)
│   ├── core/                # Konfiguratsiya, xavfsizlik, i18n, logging
│   ├── database/            # SQLAlchemy modellari, session, repositories
│   ├── providers/           # Google Books, Open Library, Local, AI providerlari
│   ├── schemas/             # Pydantic DTO modellari (BookDTO, UserDTO, AnalysisDTO)
│   ├── services/            # Qidiruv, AI tahlil, sevimlilar, o'qish ro'yxati xizmatlari
│   ├── utils/               # Transliteratsiya, matn formatlash, sahifalash
│   ├── main.py              # Telegram botni ishga tushirish nuqtasi
│   └── admin_main.py        # Admin panelni ishga tushirish nuqtasi
├── locales/                 # uz.json, ru.json, en.json tarjima fayllari
├── migrations/              # Alembic migratsiyalari
├── scripts/                 # Administrator yaratish va kitoblar to'ldirish skriptlari
├── tests/                   # 19 ta to'liq avtomatlashtirilgan pytest testlari
├── compose.yaml             # Docker Compose (Bot + Admin + PostgreSQL + Redis)
├── Dockerfile               # Production multi-stage Dockerfile
├── pyproject.toml           # Loyiha sozlamalari, dependencylar va Ruff/pytest konfiguratsiyasi
├── alembic.ini              # Alembic sozlamalari
├── .env.example             # Konfiguratsiya namunasi
└── README.md                # To'liq qo'llanma
```

---

## 🚀 O'rnatish va Ishga tushirish

### 1. Windows (PowerShell) uchun:

#### A) Virtual muhit yaratish va kutubxonalarni o'rnatish:
```powershell
# Virtual muhit yaratish
python -m venv .venv

# Virtual muhitni faollashtirish
.\.venv\Scripts\Activate.ps1

# Paketlarni o'rnatish
pip install -e .[dev]
```

#### B) .env faylini sozlash:
`.env.example` faylidan nusxa olib `.env` yarating:
```powershell
Copy-Item .env.example .env
```
Fayl ichida kamida quyidagilarni belgilang:
- `BOT_TOKEN` — [@BotFather](https://t.me/BotFather) dan olingan bot tokeni.
- `DATABASE_URL` — Mahalliy sinov uchun `sqlite+aiosqlite:///./kitobxon.db` yoki PostgreSQL URL.
- `AI_API_KEY` — Google Gemini API kaliti (ixtiyoriy, kalit bo'lmasa bot avtomatik metama'lumotlar rejimida ishlaydi).
- `ADMIN_TELEGRAM_IDS` — Sizning shaxsiy Telegram ID raqamingiz.

#### C) Boshlang'ich ma'lumotlarni yuklash:
```powershell
# Dastlabki sara kitoblar katalogini to'ldirish
python -m scripts.seed_books

# Administrator login va parolini yaratish
python -m scripts.create_admin admin adminpass123
```

#### D) Testlarni tekshirish:
```powershell
pytest -v
```

#### E) Ishga tushirish:
Telegram botni ishga tushirish:
```powershell
python -m app.main
```

FastAPI Administrator panelini alohida oynada ishga tushirish:
```powershell
python -m app.admin_main
```
Brauzer orqali oching: [http://localhost:8000/admin](http://localhost:8000/admin)
Login: `admin`, Parol: `adminpass123`

---

### 2. Linux / macOS uchun:

```bash
# Virtual muhit
python3 -m venv .venv
source .venv/bin/activate

# Paketlarni o'rnatish
pip install -e .[dev]

# .env nusxalash
cp .env.example .env

# Ma'lumotlarni to'ldirish va admin yaratish
python -m scripts.seed_books
python -m scripts.create_admin admin adminpass123

# Testlarni yurgizish
pytest -v

# Botni ishga tushirish
python -m app.main &

# Admin panelni ishga tushirish
python -m app.admin_main
```

---

### 3. Docker va Docker Compose orqali ishga tushirish (Production):

Docker orqali **PostgreSQL 16**, **Redis 7**, **Telegram Bot** va **FastAPI Admin Panel** bir vaqtning o'zida to'liq izolyatsiyalangan holda ishga tushadi:

```bash
# 1. .env faylini to'ldiring
cp .env.example .env
nano .env

# 2. Xizmatlarni ishga tushirish
docker compose up -d --build

# 3. Loglarni kuzatish
docker compose logs -f bot
docker compose logs -f admin

# 4. Konteyner ichida admin yaratish
docker compose exec admin python -m scripts.create_admin admin MaxfiyParol123!
```

---

## 🔒 Xavfsizlik va Production talablari

1. **Parollar**: PBKDF2-HMAC-SHA256 yordamida 100,000 marta aylantirilgan unikal 16-baytli salt bilan xeshlanadi. Parollar ochiq holda saqlanmaydi.
2. **Rate Limiting**: Botga va admin panelga spam hujumlarining oldini olish uchun vaqt oralig'i (0.5s) bilan cheklangan middleware o'rnatilgan.
3. **Foydalanuvchi ma'lumotlari xavfsizligi**: Foydalanuvchilarning sevimli kitoblari, qaydlari va qidiruv tarixi boshqalarga ko'rinmaydi.
4. **HTTPS va Nginx Reverse Proxy**:
   Production serverida Nginx orqali SSL sertifikat (Let's Encrypt / Certbot) o'rnating:
   ```nginx
   server {
       server_name admin.kitobxon.uz;
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
5. **Zaxira nusxalar (Backup)**:
   PostgreSQL bazasini kunlik zaxiralash:
   ```bash
   docker compose exec postgres pg_dump -U kitobxon_user kitobxon_ai > backup_$(date +%Y%m%d).sql
   ```

---

## 🧪 Avtomatlashtirilgan Testlar Natijalari

Loyiha uchun 19 ta keng qamrovli test yozilgan va 100% muvaffaqiyatli o'tgan:
- `tests/test_search.py` — Kitob qidirish, normallashtirish va foydalanuvchilar ma'lumotlari izolyatsiyasi.
- `tests/test_deduplication.py` — ISBN va nom+muallif bo'yicha takroriy kitoblarni birlashtirish.
- `tests/test_providers.py` — Google Books va Open Library API javoblarini DTO formatiga o'tkazish hamda qonuniy o'qish havolalarini aniqlash.
- `tests/test_i18n.py` — 3 ta til (O'zbek, Rus, Ingliz) kalitlarining 100% to'liqligi va interpolyatsiyasi.
- `tests/test_translit.py` — Kirill va lotin yozuvlari o'rtasidagi transliteratsiya.
- `tests/test_book_card.py` — Telegram HTML formatlash va 1024-belgi muqova caption chegarasi tekshiruvi.
- `tests/test_security.py` — PBKDF2 parol xeshlash, JWT token yaratish/tekshirish va CSRF himoyasi.
- `tests/test_ai_fallback.py` — AI API kaliti bo'lmaganda metama'lumotlar asosida tahlil qilish fallback'i.
- `tests/test_admin_api.py` — FastAPI admin panel autentifikatsiyasi, himoyalangan yo'llar va xavfsiz sessiyalar.

---

## 📋 Qaysi imkoniyatlar tekshirilgan va qaysilari sozlash talab qiladi:
- ✅ **Tekshirilgan va ishchi**: Qidiruv mexanizmi, DTO adapterlari, deduplikatsiya, lokalizatsiya (uz/ru/en), kartochka formatlash, sevimlilar, o'qish ro'yxati, profil statistikasi, admin paneli, parol xeshlash, kesh tahlillari va barcha 19 ta unit/integration testlar.
- ⚙️ **Ishga tushirish uchun kerak**:
  - `BOT_TOKEN`: [@BotFather](https://t.me/BotFather) dan olinadi.
  - `AI_API_KEY`: Google Gemini yoki OpenAI kaliti (agar kalit kiritilmasa, bot to'xtab qolmaydi — metama'lumotlar asosidagi aqlli tahlil rejimi avtomatik faollashadi).
