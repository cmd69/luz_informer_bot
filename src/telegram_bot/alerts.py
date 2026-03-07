"""Envío programado de mensajes de alerta ya generados."""
import logging
from datetime import date
from zoneinfo import ZoneInfo

from config.settings import TELEGRAM_CHAT_IDS, TIMEZONE, hora_en_franja_notificacion
from src.storage import repository as repo

logger = logging.getLogger(__name__)
TZ = ZoneInfo(TIMEZONE)


def _hora_desde_hora_envio(hora_envio: str) -> int:
    part = hora_envio.strip().split(":")[0]
    try:
        return int(part) % 24
    except ValueError:
        return -1


async def enviar_alertas_hora(bot, fecha: date, hora_envio: str) -> None:
    """Envía a todos los TELEGRAM_CHAT_IDS las alertas programadas para esta fecha y hora."""
    hora = _hora_desde_hora_envio(hora_envio)
    if hora < 0 or not hora_en_franja_notificacion(hora):
        logger.debug("No enviar alertas a %s: fuera de franja (hora=%s)", hora_envio, hora)
        return
    pendientes = repo.obtener_alertas_pendientes_hora(fecha, hora_envio)
    if not TELEGRAM_CHAT_IDS:
        logger.warning("TELEGRAM_CHAT_IDS vacío: no se enviarán alertas")
    for al in pendientes:
        for chat_id in TELEGRAM_CHAT_IDS:
            try:
                await bot.send_message(chat_id=chat_id, text=al["mensaje"])
            except Exception as e:
                logger.warning("Error enviando alerta id=%s a chat_id=%s: %s", al["id"], chat_id, e)
        repo.marcar_alerta_enviada(al["id"])
