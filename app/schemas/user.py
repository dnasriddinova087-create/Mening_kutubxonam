from datetime import datetime

from pydantic import BaseModel


class UserDTO(BaseModel):
    id: int | None = None
    telegram_id: int
    username: str | None = None
    full_name: str | None = None
    language: str = "uz"
    is_blocked: bool = False
    created_at: datetime | None = None
    last_active_at: datetime | None = None


class ReadingItemDTO(BaseModel):
    id: int | None = None
    user_id: int
    book_id: int
    status: str  # want_to_read, reading, finished
    added_at: datetime | None = None
    finished_at: datetime | None = None
