"""Entrypoint: polling del bot + scheduler."""
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
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.settings import TELEGRAM_BOT_TOKEN, TIMEZONE
from src.storage.repository import init_db
from src.telegram_bot.handlers import router
from src.telegram_bot.logging_middleware import InteractionLoggingMiddleware
from src.scheduler.jobs import job_fetch_precios, job_diseno_alertas, job_enviar_alertas_hora_async

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_bot: Optional[Bot] = None


def _get_bot() -> Bot:
    if _bot is None:
        raise RuntimeError("Bot not set")
    return _bot


async def _job_enviar_alertas() -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    hora = f"{now.hour:02d}:{now.minute:02d}"
    await job_enviar_alertas_hora_async(_get_bot(), hora)


async def set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="price", description="Precios alrededor de ahora"),
        BotCommand(command="today", description="Resumen de precios de hoy"),
        BotCommand(command="tomorrow", description="Resumen de precios de mañana"),
        BotCommand(command="fetchtoday", description="Descargar precios de hoy"),
        BotCommand(command="fetchtomorrow", description="Descargar precios de mañana"),
        BotCommand(command="ask", description="Preguntar a la IA sobre precios"),
        BotCommand(command="models", description="Listar o elegir modelo de IA"),
        BotCommand(command="help", description="Ver todos los comandos"),
        BotCommand(command="testollama", description="Probar conexión con Ollama"),
        BotCommand(command="generate_tips", description="Obtener precios y generar alertas"),
        BotCommand(command="show_alerts", description="Ver alertas programadas de hoy"),
        BotCommand(command="test_alerts", description="Ver la próxima alerta pendiente"),
        BotCommand(command="notificaciones", description="Activar/desactivar alertas automáticas"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    global _bot
    init_db()
    _bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await set_bot_commands(_bot)
    logger.info("Comandos del bot registrados en Telegram")

    dp = Dispatcher()
    router.message.middleware(InteractionLoggingMiddleware())
    dp.include_router(router)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_fetch_precios, "cron", hour=20, minute=30, timezone=TIMEZONE)
    scheduler.add_job(job_diseno_alertas, "cron", hour=21, minute=0, timezone=TIMEZONE)
    scheduler.add_job(_job_enviar_alertas, "cron", minute="0,30", timezone=TIMEZONE)
    scheduler.start()

    await dp.start_polling(_bot)


if __name__ == "__main__":
    asyncio.run(main())
