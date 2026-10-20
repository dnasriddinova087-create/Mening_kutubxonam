import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.models import Book, User
from app.database.repositories.admin_repo import AdminRepository
from app.database.repositories.book_repo import BookRepository
from app.schemas.book import BookDTO
from app.utils.text import escape_html

router = Router(name="admin_bot")


class AdminBookStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_authors = State()
    waiting_for_language = State()
    waiting_for_genres = State()
    waiting_for_description = State()
    waiting_for_cover = State()
    waiting_for_file = State()
    waiting_for_audio = State()
    waiting_for_video = State()
    waiting_for_pages = State()


class AdminBroadcastStates(StatesGroup):
    waiting_for_text = State()


def is_admin(user_id: int | None) -> bool:
    """Check if telegram user ID belongs to authorized administrators."""
    if not user_id:
        return False
    return user_id in settings.ADMIN_TELEGRAM_IDS


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Main administrative dashboard keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Yangi kitob qo'shish", callback_data="admin:book:add"),
                InlineKeyboardButton(text="📚 Kitoblar ro'yxati (#kod)", callback_data="admin:books:1"),
            ],
            [
                InlineKeyboardButton(text="🔢 Kod bo'yicha boshqarish", callback_data="admin:book:by_code"),
                InlineKeyboardButton(text="📢 Ommaviy xabar (Broadcast)", callback_data="admin:broadcast"),
            ],
            [
                InlineKeyboardButton(text="📊 Batafsil statistika", callback_data="admin:stats"),
                InlineKeyboardButton(text="🌐 Web Panel ma'lumotlari", callback_data="admin:web_info"),
            ],
            [
                InlineKeyboardButton(text="🔄 Kodlarni qayta sinxronlash", callback_data="admin:sync_codes"),
            ],
        ]
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession):
    """Handle /admin command for super administrators."""
    if not is_admin(message.from_user.id if message.from_user else None):
        return

    admin_repo = AdminRepository(session)
    stats = await admin_repo.get_dashboard_stats()

    # Calculate media counts
    audio_count = (
        await session.execute(select(func.count(Book.id)).where(Book.audio_url.is_not(None)))
    ).scalar() or 0
    video_count = (
        await session.execute(select(func.count(Book.id)).where(Book.video_url.is_not(None)))
    ).scalar() or 0
    file_count = (
        await session.execute(select(func.count(Book.id)).where(Book.file_url.is_not(None)))
    ).scalar() or 0

    text = (
        "👑 <b>KITOBXON AI — SUPER ADMINISTRATOR PANELI</b>\n\n"
        f"👤 <b>Administrator:</b> {escape_html(message.from_user.full_name or 'Super Admin')} "
        f"(ID: <code>{message.from_user.id}</code>)\n"
        "🔰 <b>Ruxsat darajasi:</b> Super Admin (To'liq huquq)\n"
        "🟢 <b>Tizim holati:</b> Online / Faol\n\n"
        "📊 <b>Kutubxona statistikasi:</b>\n"
        f"• 📚 Jami kitoblar: <b>{stats.get('total_books', 0)}</b> ta\n"
        f"• 👥 Foydalanuvchilar: <b>{stats.get('total_users', 0)}</b> ta\n"
        f"• 🔍 Amalga oshirilgan qidiruvlar: <b>{stats.get('total_searches', 0)}</b> ta\n"
        f"• 🎧 Audiokitoblar: <b>{audio_count}</b> ta\n"
        f"• 🎬 Video sharhlar: <b>{video_count}</b> ta\n"
        f"• 📥 Elektron fayllar (PDF/EPUB): <b>{file_count}</b> ta\n\n"
        "<i>Kerakli boshqaruv amalini tanlang:</i>"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=get_admin_main_keyboard())


@router.callback_query(F.data == "admin:main")
async def cb_admin_main(callback: CallbackQuery, session: AsyncSession):
    """Return to admin main menu."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    admin_repo = AdminRepository(session)
    stats = await admin_repo.get_dashboard_stats()
    text = (
        "👑 <b>KITOBXON AI — ADMINISTRATOR PANELI</b>\n\n"
        f"📚 Jami kitoblar: <b>{stats.get('total_books', 0)}</b> ta | "
        f"👥 Foydalanuvchilar: <b>{stats.get('total_users', 0)}</b> ta\n\n"
        "<i>Kerakli bo'limni tanlang:</i>"
    )
    if callback.message:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(callback: CallbackQuery, session: AsyncSession):
    """View advanced stats."""
    if not is_admin(callback.from_user.id):
        return

    admin_repo = AdminRepository(session)
    stats = await admin_repo.get_dashboard_stats()

    lang_stats = stats.get("lang_stats", {})
    lang_lines = "\n".join([f"  • {k.upper()}: {v} ta" for k, v in lang_stats.items()]) or "  • Ma'lumot yo'q"

    text = (
        "📊 <b>KENGAYTIRILGAN STATISTIKA VA HISOBOTLAR</b>\n\n"
        f"👥 <b>Foydalanuvchilar:</b>\n"
        f"• Jami: <b>{stats.get('total_users', 0)}</b>\n"
        f"• Bugun qo'shilgan: <b>{stats.get('registered_today', 0)}</b>\n"
        f"• Bugun faol bo'lgan: <b>{stats.get('active_today', 0)}</b>\n"
        f"• Shu oyda faol: <b>{stats.get('active_month', 0)}</b>\n\n"
        f"🌐 <b>Foydalanuvchilar tili:</b>\n{lang_lines}\n\n"
        f"🔍 <b>Qidiruvlar:</b>\n"
        f"• Jami: <b>{stats.get('total_searches', 0)}</b>\n"
        f"• Bugungi: <b>{stats.get('today_searches', 0)}</b>\n"
        f"• Sevimlilarga qo'shilgan: <b>{stats.get('total_favorites', 0)}</b>"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Boshqaruv menyusiga qaytish", callback_data="admin:main")]]
    )
    if callback.message:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "admin:web_info")
async def cb_admin_web_info(callback: CallbackQuery):
    """Show Web Admin Panel connection info."""
    if not is_admin(callback.from_user.id):
        return

    text = (
        "🌐 <b>FASTAPI WEB ADMINISTRATOR PANELI</b>\n\n"
        "Web panel orqali kitoblarni jadval ko'rinishida tahrirlash, audio/video/PDF fayllarni yuklash, "
        "kategoriyalarni sozlash va foydalanuvchilar auditini kuzatish mumkin.\n\n"
        f"🔗 <b>Web manzil:</b> <code>{settings.PUBLIC_BASE_URL}/admin</code>\n"
        "🔑 <b>Kirish:</b> Super Admin hisobi orqali\n\n"
        "<i>Eslatma: Web panel local yoki serverda port 8000 da ishlamoqda.</i>"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Web Panelni ochish", url=f"{settings.PUBLIC_BASE_URL}/admin")],
            [InlineKeyboardButton(text="🔙 Qaytish", callback_data="admin:main")],
        ]
    )
    if callback.message:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "admin:sync_codes")
async def cb_admin_sync_codes(callback: CallbackQuery, session: AsyncSession):
    """Sync and assign sequential codes to any books missing a code."""
    if not is_admin(callback.from_user.id):
        return

    repo = BookRepository(session)
    count = await repo.assign_missing_codes()
    await callback.answer(f"Sinxronlash yakunlandi: {count} ta kitobga yangi kod biriktirildi!", show_alert=True)


# --- Add Book Wizard ---

@router.callback_query(F.data == "admin:book:add")
async def cb_admin_book_add_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Start step-by-step book creation wizard in Telegram."""
    if not is_admin(callback.from_user.id):
        return

    repo = BookRepository(session)
    next_code = await repo.get_next_book_code()
    await state.set_state(AdminBookStates.waiting_for_title)
    await state.update_data(next_code=next_code)

    text = (
        f"➕ <b>YANGI KITOB QO'SHISH (Avtomatik kod: #{next_code})</b>\n\n"
        "1-qadam: Kitobning to'liq nomini kiriting:\n\n"
        "<i>Bekor qilish uchun /cancel yuboring.</i>"
    )
    if callback.message:
        await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.message(AdminBookStates.waiting_for_title)
async def process_book_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    if not title:
        await message.answer("Kitob nomi bo'sh bo'lishi mumkin emas. Qayta kiriting:")
        return

    await state.update_data(title=title)
    await state.set_state(AdminBookStates.waiting_for_authors)
    await message.answer("2-qadam: Muallif(lar) ismini kiriting (bir nechta bo'lsa vergul bilan ajrating):")


@router.message(AdminBookStates.waiting_for_authors)
async def process_book_authors(message: Message, state: FSMContext):
    authors_text = (message.text or "").strip()
    authors = [a.strip() for a in authors_text.split(",") if a.strip()] or ["Noma'lum muallif"]

    await state.update_data(authors=authors)
    await state.set_state(AdminBookStates.waiting_for_language)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha (uz)", callback_data="admin:lang:uz"),
                InlineKeyboardButton(text="🇷🇺 Ruscha (ru)", callback_data="admin:lang:ru"),
                InlineKeyboardButton(text="🇬🇧 Inglizcha (en)", callback_data="admin:lang:en"),
            ]
        ]
    )
    await message.answer("3-qadam: Kitobning asosiy tilini tanlang:", reply_markup=kb)


@router.callback_query(F.data.startswith("admin:lang:"), AdminBookStates.waiting_for_language)
async def process_book_language(callback: CallbackQuery, state: FSMContext):
    lang_code = callback.data.split(":")[2]
    await state.update_data(language=lang_code)
    await state.set_state(AdminBookStates.waiting_for_genres)
    await callback.answer()

    if callback.message:
        await callback.message.answer(
            "4-qadam: Kitob janrlarini kiriting (masalan: <i>Badiiy, Tarixiy, Roman</i>):",
            parse_mode="HTML",
        )


@router.message(AdminBookStates.waiting_for_genres)
async def process_book_genres(message: Message, state: FSMContext):
    genres_text = (message.text or "").strip()
    genres = [g.strip() for g in genres_text.split(",") if g.strip()] or ["Badiiy"]

    await state.update_data(genres=genres)
    await state.set_state(AdminBookStates.waiting_for_description)
    await message.answer(
        "5-qadam: Kitobning tavsifi va qisqacha mazmunini kiriting:\n(Agar yo'q bo'lsa 'otkazish' deb yozing)"
    )


@router.message(AdminBookStates.waiting_for_description)
async def process_book_description(message: Message, state: FSMContext):
    desc = (message.text or "").strip()
    if desc.lower() in ("otkazish", "yo'q", "yoq", "skip", "-"):
        desc = ""

    await state.update_data(description=desc)
    await state.set_state(AdminBookStates.waiting_for_cover)
    await message.answer(
        "6-qadam: Muqova rasmi URL havolasini yuboring (yoki rasmni to'g'ridan-to'g'ri yuboring / 'otkazish'):"
    )


@router.message(AdminBookStates.waiting_for_cover)
async def process_book_cover(message: Message, state: FSMContext):
    cover_url = None
    if message.photo:
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        if file.file_path:
            cover_url = f"https://api.telegram.org/file/bot{settings.BOT_TOKEN}/{file.file_path}"
    elif message.text:
        text = message.text.strip()
        if text.startswith("http://") or text.startswith("https://"):
            cover_url = text

    await state.update_data(cover_url=cover_url)
    await state.set_state(AdminBookStates.waiting_for_file)
    await message.answer(
        "7-qadam: Elektron kitob (PDF, EPUB) havolasini kiriting (yoki 'otkazish'):"
    )


@router.message(AdminBookStates.waiting_for_file)
async def process_book_file(message: Message, state: FSMContext):
    file_url = None
    if message.text and message.text.strip().startswith("http"):
        file_url = message.text.strip()

    await state.update_data(file_url=file_url)
    await state.set_state(AdminBookStates.waiting_for_audio)
    await message.answer(
        "8-qadam: Audiokitob havolasi (MP3 / Havola) mavjud bo'lsa kiriting (yoki 'otkazish'):"
    )


@router.message(AdminBookStates.waiting_for_audio)
async def process_book_audio(message: Message, state: FSMContext):
    audio_url = None
    if message.text and message.text.strip().startswith("http"):
        audio_url = message.text.strip()

    await state.update_data(audio_url=audio_url)
    await state.set_state(AdminBookStates.waiting_for_video)
    await message.answer(
        "9-qadam: Video sharh / taqdimot havolasi (YouTube / Havola) mavjud bo'lsa kiriting (yoki 'otkazish'):"
    )


@router.message(AdminBookStates.waiting_for_video)
async def process_book_video(message: Message, state: FSMContext, session: AsyncSession):
    video_url = None
    if message.text and message.text.strip().startswith("http"):
        video_url = message.text.strip()

    data = await state.get_data()
    await state.clear()

    repo = BookRepository(session)
    admin_repo = AdminRepository(session)

    import uuid
    source_book_id = f"local_{uuid.uuid4().hex[:8]}"

    dto = BookDTO(
        source="local",
        source_book_id=source_book_id,
        title=data.get("title", "Nomsiz"),
        authors=data.get("authors", []),
        language=data.get("language", "uz"),
        genres=data.get("genres", []),
        description=data.get("description") or None,
        cover_url=data.get("cover_url"),
        file_url=data.get("file_url"),
        file_format="PDF",
        audio_url=data.get("audio_url"),
        video_url=video_url,
        access_type="free" if data.get("file_url") else "info",
    )

    created_book = await repo.upsert_from_dto(dto)

    await admin_repo.log_audit(
        admin_id=None,
        action="bot_create_book",
        target_type="book",
        target_id=str(created_book.id),
        details={"title": created_book.original_title, "code": created_book.code},
    )

    success_text = (
        "✅ <b>KITOB MUVAFFAQIYATLI SAQLANDI!</b>\n\n"
        f"📖 <b>Nomi:</b> {escape_html(created_book.original_title)}\n"
        f"✍️ <b>Muallif:</b> {escape_html(', '.join(created_book.authors))}\n"
        f"🆔 <b>Avtomatik kitob kodi:</b> <code>#{created_book.code}</code>\n"
        f"🌐 <b>Tili:</b> {created_book.language.upper()}\n"
        f"🏷️ <b>Janr:</b> {escape_html(', '.join(created_book.genres))}\n\n"
        "Foydalanuvchilar ushbu kitobni katalogda ko'rishlari va <code>#"
        f"{created_book.code}</code> kodini yuborib bir zumda topishlari mumkin!"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📖 Kitob kartochkasini ko'rish", callback_data=f"book:view:{created_book.id}")],
            [InlineKeyboardButton(text="🔙 Boshqaruv paneliga qaytish", callback_data="admin:main")],
        ]
    )
    await message.answer(success_text, parse_mode="HTML", reply_markup=kb)


# --- Broadcast Wizard ---

@router.callback_query(F.data == "admin:broadcast")
async def cb_admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Start broadcast announcement message."""
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminBroadcastStates.waiting_for_text)
    text = (
        "📢 <b>OMMAVIY XABAR (BROADCAST) YUBORISH</b>\n\n"
        "Botning barcha ro'yxatdan o'tgan foydalanuvchilariga yuboriladigan xabar matnini kiriting:\n\n"
        "<i>Bekor qilish uchun /cancel yuboring.</i>"
    )
    if callback.message:
        await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.message(AdminBroadcastStates.waiting_for_text)
async def process_broadcast_text(message: Message, state: FSMContext, session: AsyncSession):
    broadcast_text = message.text or message.caption or ""
    if not broadcast_text.strip():
        await message.answer("Xabar matni bo'sh bo'lishi mumkin emas. Qayta yuboring:")
        return

    await state.clear()
    stmt = select(User.telegram_id).where(User.is_blocked.is_(False))
    user_ids = (await session.execute(stmt)).scalars().all()

    status_msg = await message.answer(f"⏳ Xabar {len(user_ids)} ta foydalanuvchiga yuborilmoqda...")

    success = 0
    failed = 0
    for uid in user_ids:
        try:
            await message.bot.send_message(chat_id=uid, text=broadcast_text, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.04)  # Rate limiting ~25 msgs/sec
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ <b>Xabar yuborish yakunlandi!</b>\n\n"
        f"• Muvaffaqiyatli: <b>{success}</b> ta\n"
        f"• Yetib bormadi (bloklangan/xato): <b>{failed}</b> ta",
        parse_mode="HTML",
    )
