import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from app.bot.handlers import (
    book_detail,
    errors,
    favorites,
    language,
    profile,
    reading_list,
    recommendations,
    search,
    start,
)
from app.bot.middlewares.db_session import DbSessionMiddleware
from app.bot.middlewares.i18n import I18nMiddleware
from app.bot.middlewares.rate_limit import RateLimitMiddleware
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.database.session import init_db


async def register_bot_commands(bot: Bot) -> None:
    """Register commands for BotFather in uz, ru, and en."""
    commands_uz = [
        BotCommand(command="start", description="Bosh menyuni ochish"),
        BotCommand(command="search", description="Kitob qidirish"),
        BotCommand(command="favorites", description="Sevimli kitoblarim"),
        BotCommand(command="profile", description="Profil va statistika"),
        BotCommand(command="recommend", description="Kitob tavsiyalari"),
        BotCommand(command="language", description="Tilni o'zgartirish"),
        BotCommand(command="help", description="Yordam yo'riqnomasi"),
        BotCommand(command="cancel", description="Amalni bekor qilish"),
    ]

    commands_ru = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="search", description="Поиск книг"),
        BotCommand(command="favorites", description="Мои избранные"),
        BotCommand(command="profile", description="Профиль и статистика"),
        BotCommand(command="recommend", description="Рекомендации книг"),
        BotCommand(command="language", description="Смена языка"),
        BotCommand(command="help", description="Помощь и команды"),
        BotCommand(command="cancel", description="Отмена действия"),
    ]

    commands_en = [
        BotCommand(command="start", description="Open main menu"),
        BotCommand(command="search", description="Search books"),
        BotCommand(command="favorites", description="My favorite books"),
        BotCommand(command="profile", description="Profile & statistics"),
        BotCommand(command="recommend", description="Book recommendations"),
        BotCommand(command="language", description="Switch language"),
        BotCommand(command="help", description="Help guide"),
        BotCommand(command="cancel", description="Cancel action"),
    ]

    try:
        await bot.set_my_commands(commands_uz, scope=BotCommandScopeDefault())
        await bot.set_my_commands(commands_ru, scope=BotCommandScopeDefault(), language_code="ru")
        await bot.set_my_commands(commands_en, scope=BotCommandScopeDefault(), language_code="en")
        logger.info("BotFather commands registered successfully.")
    except Exception as e:
        logger.warning(f"Could not register BotFather commands: {e}")


async def get_fsm_storage():
    """Returns RedisStorage if Redis is reachable, otherwise MemoryStorage."""
    if settings.REDIS_URL:
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
            await r.ping()
            await r.aclose()
            logger.info("Connected to Redis FSM storage.")
            return RedisStorage.from_url(settings.REDIS_URL)
        except Exception:
            logger.info("Redis is offline or not running. Using in-memory FSM storage fallback.")
    return MemoryStorage()


async def main() -> None:
    setup_logging()
    logger.info("Starting KITOBXON AI Bot...")

    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN is not configured! Please provide BOT_TOKEN in .env file.")
        return

    # Initialize Database
    await init_db()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    storage = await get_fsm_storage()
    dp = Dispatcher(storage=storage)

    # Register Middlewares
    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(I18nMiddleware())
    dp.message.middleware(RateLimitMiddleware(limit_seconds=0.5))
    dp.callback_query.middleware(RateLimitMiddleware(limit_seconds=0.5))

    # Include Handlers
    dp.include_router(start.router)
    dp.include_router(search.router)
    dp.include_router(book_detail.router)
    dp.include_router(favorites.router)
    dp.include_router(reading_list.router)
    dp.include_router(profile.router)
    dp.include_router(recommendations.router)
    dp.include_router(language.router)
    dp.include_router(errors.router)

    # Setup BotFather menu commands
    await register_bot_commands(bot)

    try:
        logger.info("Bot polling started.")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
