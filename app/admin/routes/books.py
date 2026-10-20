import uuid

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.dependencies import AdminRole, require_roles
from app.database.models import Admin
from app.database.repositories.admin_repo import AdminRepository
from app.database.repositories.book_repo import BookRepository
from app.database.session import get_db
from app.schemas.book import BookDTO

router = APIRouter(prefix="/admin/books", tags=["admin_books"])
templates = Jinja2Templates(directory="app/admin/templates")


@router.get("", response_class=HTMLResponse)
async def list_books_page(
    request: Request,
    q: str | None = None,
    admin: Admin = Depends(require_roles(AdminRole.BOOK_MANAGER, AdminRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    repo = BookRepository(session)
    if q and q.strip():
        clean_q = q.strip()
        if clean_q.isdigit():
            book_by_code = await repo.get_by_code(int(clean_q))
            if book_by_code:
                books = [book_by_code]
            else:
                books, _ = await repo.search_local(clean_q, offset=0, limit=50, include_archived=True)
        else:
            books, _ = await repo.search_local(clean_q, offset=0, limit=50, include_archived=True)
    else:
        books, _ = await repo.list_books(offset=0, limit=50, include_archived=True)

    return templates.TemplateResponse(
        request=request,
        name="books.html",
        context={
            "admin": admin,
            "active_tab": "books",
            "books": books,
            "search_query": q,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_book_page(
    request: Request,
    admin: Admin = Depends(require_roles(AdminRole.BOOK_MANAGER, AdminRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    repo = BookRepository(session)
    next_code = await repo.get_next_book_code()
    return templates.TemplateResponse(
        request=request,
        name="book_form.html",
        context={
            "admin": admin,
            "active_tab": "books",
            "book": None,
            "next_code": next_code,
        },
    )


@router.post("/new")
async def create_book_submit(
    title: str = Form(...),
    authors: str = Form(...),
    description: str | None = Form(None),
    language: str | None = Form("uz"),
    genres: str | None = Form(None),
    publisher: str | None = Form(None),
    published_date: str | None = Form(None),
    isbn: str | None = Form(None),
    access_type: str = Form("info"),
    cover_url: str | None = Form(None),
    reading_url: str | None = Form(None),
    code: int | None = Form(None),
    file_url: str | None = Form(None),
    file_format: str | None = Form("PDF"),
    audio_url: str | None = Form(None),
    audio_duration: str | None = Form(None),
    video_url: str | None = Form(None),
    pages: int | None = Form(None),
    book_status: str | None = Form("published"),
    admin: Admin = Depends(require_roles(AdminRole.BOOK_MANAGER, AdminRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    repo = BookRepository(session)
    admin_repo = AdminRepository(session)

    authors_list = [a.strip() for a in authors.split(",") if a.strip()]
    genres_list = [g.strip() for g in genres.split(",") if g.strip()] if genres else []
    source_book_id = f"local_{uuid.uuid4().hex[:8]}"

    dto = BookDTO(
        source="local",
        source_book_id=source_book_id,
        code=code,
        title=title.strip(),
        authors=authors_list,
        description=description.strip() if description else None,
        language=language.strip().lower() if language else "uz",
        genres=genres_list,
        publisher=publisher.strip() if publisher else None,
        published_date=published_date.strip() if published_date else None,
        isbn=isbn.strip() if isbn else None,
        access_type=access_type,
        cover_url=cover_url.strip() if cover_url else None,
        reading_url=reading_url.strip() if reading_url else None,
        file_url=file_url.strip() if file_url else None,
        file_format=file_format.strip() if file_format else "PDF",
        audio_url=audio_url.strip() if audio_url else None,
        audio_duration=audio_duration.strip() if audio_duration else None,
        video_url=video_url.strip() if video_url else None,
        pages=pages,
        status=book_status or "published",
    )

    created_book = await repo.upsert_from_dto(dto)

    await admin_repo.log_audit(
        admin_id=admin.id,
        action="create_book",
        target_type="book",
        target_id=str(created_book.id),
        details={"title": title, "code": created_book.code, "language": language},
    )

    return RedirectResponse(url="/admin/books", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{book_id}/edit", response_class=HTMLResponse)
async def edit_book_page(
    book_id: int,
    request: Request,
    admin: Admin = Depends(require_roles(AdminRole.BOOK_MANAGER, AdminRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    repo = BookRepository(session)
    book = await repo.get_by_id(book_id)
    if not book:
        return RedirectResponse(url="/admin/books")

    return templates.TemplateResponse(
        request=request,
        name="book_form.html",
        context={
            "admin": admin,
            "active_tab": "books",
            "book": book,
            "next_code": book.code,
        },
    )


@router.post("/{book_id}/edit")
async def edit_book_submit(
    book_id: int,
    title: str = Form(...),
    authors: str = Form(...),
    description: str | None = Form(None),
    language: str | None = Form("uz"),
    genres: str | None = Form(None),
    publisher: str | None = Form(None),
    published_date: str | None = Form(None),
    isbn: str | None = Form(None),
    access_type: str = Form("info"),
    cover_url: str | None = Form(None),
    reading_url: str | None = Form(None),
    code: int | None = Form(None),
    file_url: str | None = Form(None),
    file_format: str | None = Form("PDF"),
    audio_url: str | None = Form(None),
    audio_duration: str | None = Form(None),
    video_url: str | None = Form(None),
    pages: int | None = Form(None),
    book_status: str | None = Form("published"),
    admin: Admin = Depends(require_roles(AdminRole.BOOK_MANAGER, AdminRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    repo = BookRepository(session)
    admin_repo = AdminRepository(session)

    authors_list = [a.strip() for a in authors.split(",") if a.strip()]
    genres_list = [g.strip() for g in genres.split(",") if g.strip()] if genres else []

    await repo.update_book_details(
        book_id=book_id,
        title=title.strip(),
        authors=authors_list,
        description=description.strip() if description else None,
        cover_url=cover_url.strip() if cover_url else None,
        publisher=publisher.strip() if publisher else None,
        published_date=published_date.strip() if published_date else None,
        isbn=isbn.strip() if isbn else None,
        access_type=access_type,
        reading_url=reading_url.strip() if reading_url else None,
        language=language.strip().lower() if language else None,
        genres=genres_list,
        code=code,
        file_url=file_url.strip() if file_url else None,
        file_format=file_format.strip() if file_format else "PDF",
        audio_url=audio_url.strip() if audio_url else None,
        audio_duration=audio_duration.strip() if audio_duration else None,
        video_url=video_url.strip() if video_url else None,
        pages=pages,
        status=book_status or "published",
    )

    await admin_repo.log_audit(
        admin_id=admin.id,
        action="update_book",
        target_type="book",
        target_id=str(book_id),
        details={"title": title, "code": code, "language": language},
    )

    return RedirectResponse(url="/admin/books", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{book_id}/toggle-archive")
async def toggle_archive_book(
    book_id: int,
    admin: Admin = Depends(require_roles(AdminRole.BOOK_MANAGER, AdminRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    repo = BookRepository(session)
    admin_repo = AdminRepository(session)

    book = await repo.get_by_id(book_id)
    if book:
        new_status = not book.is_archived
        await repo.set_archived(book_id, new_status)
        await admin_repo.log_audit(
            admin_id=admin.id,
            action="archive_book" if new_status else "unarchive_book",
            target_type="book",
            target_id=str(book_id),
        )

    return RedirectResponse(url="/admin/books", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{book_id}/delete")
async def delete_book_submit(
    book_id: int,
    admin: Admin = Depends(require_roles(AdminRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    repo = BookRepository(session)
    admin_repo = AdminRepository(session)

    book = await repo.get_by_id(book_id)
    if book:
        title = book.original_title
        await repo.delete_book(book_id)
        await admin_repo.log_audit(
            admin_id=admin.id,
            action="delete_book",
            target_type="book",
            target_id=str(book_id),
            details={"title": title},
        )

    return RedirectResponse(url="/admin/books", status_code=status.HTTP_303_SEE_OTHER)
