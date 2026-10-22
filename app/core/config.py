
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram Bot
    BOT_TOKEN: str = Field(default="", description="Telegram Bot API Token from @BotFather")

    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./kitobxon.db",
        description="Async SQLAlchemy database URL (PostgreSQL or SQLite)",
    )

    # Redis (Optional: if offline or unavailable, memory fallback is used)
    REDIS_URL: str | None = Field(default="redis://localhost:6379/0")

    # Google Books
    GOOGLE_BOOKS_API_KEY: str | None = Field(default=None)

    # AI Analysis
    AI_PROVIDER: str = Field(default="gemini", description="gemini | openai | mock")
    AI_API_KEY: str | None = Field(default=None)
    AI_MODEL: str = Field(default="gemini-1.5-flash")

    # Administration
    ADMIN_TELEGRAM_IDS: list[int] = Field(default_factory=lambda: [8154138330])
    ADMIN_SESSION_SECRET: str = Field(default="super-secret-default-key-change-in-prod")
    ADMIN_HOST: str = Field(default="0.0.0.0")
    ADMIN_PORT: int = Field(default=8000)

    # Public base URL
    PUBLIC_BASE_URL: str = Field(default="http://localhost:8000")

    PORT: int | None = Field(default=None, description="Cloud provider assigned port (e.g. Render)")
    AUTO_SEED: bool = Field(default=True, description="Auto-seed books if catalog is empty")
    DEFAULT_ADMIN_USER: str = Field(default="admin")
    DEFAULT_ADMIN_PASSWORD: str = Field(default="adminpass123")

    # Logging
    LOG_LEVEL: str = Field(default="INFO")

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v):
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and not v.startswith("postgresql+"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("ADMIN_TELEGRAM_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, int):
            return [v]
        return v or []

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def effective_admin_port(self) -> int:
        return self.PORT or self.ADMIN_PORT


settings = Settings()

