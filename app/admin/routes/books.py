import uuid

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.dependencies import get_current_admin
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
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    repo = BookRepository(session)
    if q and q.strip():
        books, _ = await repo.search_local(q.strip(), offset=0, limit=50, include_archived=True)
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
    admin: Admin = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="book_form.html",
        context={
            "admin": admin,
            "active_tab": "books",
            "book": None,
        },
    )


@router.post("/new")
async def create_book_submit(
    title: str = Form(...),
    authors: str = Form(...),
    description: str | None = Form(None),
    publisher: str | None = Form(None),
    published_date: str | None = Form(None),
    isbn: str | None = Form(None),
    access_type: str = Form("info"),
    cover_url: str | None = Form(None),
    reading_url: str | None = Form(None),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    repo = BookRepository(session)
    admin_repo = AdminRepository(session)

    authors_list = [a.strip() for a in authors.split(",") if a.strip()]
    source_book_id = f"local_{uuid.uuid4().hex[:8]}"

    dto = BookDTO(
        source="local",
        source_book_id=source_book_id,
        title=title.strip(),
        authors=authors_list,
        description=description.strip() if description else None,
        publisher=publisher.strip() if publisher else None,
        published_date=published_date.strip() if published_date else None,
        isbn=isbn.strip() if isbn else None,
        access_type=access_type,
        cover_url=cover_url.strip() if cover_url else None,
        reading_url=reading_url.strip() if reading_url else None,
    )

    created_book = await repo.upsert_from_dto(dto)

    await admin_repo.log_audit(
        admin_id=admin.id,
        action="create_book",
        target_type="book",
        target_id=str(created_book.id),
        details={"title": title},
    )

    return RedirectResponse(url="/admin/books", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{book_id}/edit", response_class=HTMLResponse)
async def edit_book_page(
    book_id: int,
    request: Request,
    admin: Admin = Depends(get_current_admin),
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
        },
    )


@router.post("/{book_id}/edit")
async def edit_book_submit(
    book_id: int,
    title: str = Form(...),
    authors: str = Form(...),
    description: str | None = Form(None),
    publisher: str | None = Form(None),
    published_date: str | None = Form(None),
    isbn: str | None = Form(None),
    access_type: str = Form("info"),
    cover_url: str | None = Form(None),
    reading_url: str | None = Form(None),
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    repo = BookRepository(session)
    admin_repo = AdminRepository(session)

    authors_list = [a.strip() for a in authors.split(",") if a.strip()]

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
    )

    await admin_repo.log_audit(
        admin_id=admin.id,
        action="update_book",
        target_type="book",
        target_id=str(book_id),
        details={"title": title},
    )

    return RedirectResponse(url="/admin/books", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{book_id}/toggle-archive")
async def toggle_archive_book(
    book_id: int,
    admin: Admin = Depends(get_current_admin),
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
