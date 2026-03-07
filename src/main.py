"""Entrypoint: polling del bot (sin scheduler en este commit)."""
import asyncio
import logging
from pathlib import Path
from typing import Optional

_root = Path(__file__).resolve().parent.parent
if str(_root) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_root))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config.settings import TELEGRAM_BOT_TOKEN
from src.storage.repository import init_db
from src.telegram_bot.handlers import router
from src.telegram_bot.logging_middleware import InteractionLoggingMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="price", description="Precios alrededor de ahora"),
        BotCommand(command="today", description="Resumen de precios de hoy"),
        BotCommand(command="tomorrow", description="Resumen de precios de mañana"),
        BotCommand(command="help", description="Ver todos los comandos"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    init_db()
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await set_bot_commands(bot)
    logger.info("Comandos del bot registrados en Telegram")

    dp = Dispatcher()
    router.message.middleware(InteractionLoggingMiddleware())
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
