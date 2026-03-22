"""Jobs: fetch precios 1/día, diseño de alertas 1/día, envío a horas indicadas."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config.settings import TIMEZONE
from src.precios.tarifaluzhora import fetch_precios_dia
from src.storage import repository as repo

TZ = ZoneInfo(TIMEZONE)


def job_fetch_precios() -> None:
    """Obtener precios de hoy y mañana y guardar. Ejecutar 1 vez al día (ej. 22:00)."""
    hoy = datetime.now(TZ).date()
    manana = hoy + timedelta(days=1)
    for delta in (0, 1):
        f = hoy + timedelta(days=delta)
        precios, web_date = fetch_precios_dia(f)
        if precios:
            repo.guardar_precios_dia(precios.fecha, [(t.hora, t.precio) for t in precios.tramos_ordenados()])
        elif web_date is not None and web_date != f and f == hoy:
            repo.borrar_precios_fecha(manana)


def job_retry_fetch_manana() -> None:
    """Reintentar fetch de mañana si no hay datos. Ejecutar como fallback (ej. 23:59)."""
    hoy = datetime.now(TZ).date()
    manana = hoy + timedelta(days=1)
    tramos_manana = repo.contar_tramos_fecha(manana)
    if tramos_manana >= 24:
        logger.info("Mañana ya tiene %d tramos, no hace falta reintentar.", tramos_manana)
        return
    logger.info("Mañana tiene %d tramos (<24), reintentando fetch...", tramos_manana)
    precios, web_date = fetch_precios_dia(manana)
    if precios:
        repo.guardar_precios_dia(precios.fecha, [(t.hora, t.precio) for t in precios.tramos_ordenados()])
        logger.info("✅ Reintentom éxito: %d tramos guardados para %s", len(precios.tramos), manana)
    else:
        logger.warning("⚠️ Reintento fallido: no se pudieron obtener precios para %s", manana)


async def job_diseno_alertas() -> None:
    from src.scheduler.alertas_ia import job_diseno_alertas as _job
    await _job()


async def job_enviar_alertas_hora_async(bot, hora: str) -> None:
    """Enviar alertas programadas para la hora dada (formato 'HH' o 'HH:MM')."""
    from src.telegram_bot.alerts import enviar_alertas_hora
    hoy = datetime.now(TZ).date()
    await enviar_alertas_hora(bot, hoy, hora)
