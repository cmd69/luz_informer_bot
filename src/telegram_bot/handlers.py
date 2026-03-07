"""Telegram handlers: /start, /help, /price, /today, /tomorrow, /fetchtoday, /fetchtomorrow."""
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from config.settings import TELEGRAM_CHAT_IDS, TIMEZONE, get_umbrales_fecha
from src.precios.models import PreciosDia, TramoPrecio
from src.precios.tarifaluzhora import fetch_precios_dia
from src.storage import repository as repo

logger = logging.getLogger(__name__)
router = Router()
TZ = ZoneInfo(TIMEZONE)


def _chat_permitido(chat_id: int) -> bool:
    if not TELEGRAM_CHAT_IDS:
        return True
    return str(chat_id) in TELEGRAM_CHAT_IDS


async def _reject_if_not_allowed(message: Message) -> bool:
    if _chat_permitido(message.chat.id):
        return False
    await message.answer(
        "No tienes permiso para usar este bot. Añade tu chat_id a TELEGRAM_CHAT_IDS en .env.\n"
        "(Puedes obtener tu chat_id con @userinfobot)"
    )
    return True


def _fecha_hoy() -> date:
    return datetime.now(TZ).date()


def _hora_actual() -> int:
    return datetime.now(TZ).hour


def _get_smart_time_range(hora_actual: int, precios_dia: PreciosDia) -> list[tuple[int, float]]:
    """3 h antes + actual + 3 h después; al final/inicio del día incluye mañana/ayer si hay datos."""
    hoy = precios_dia.fecha
    manana = hoy + timedelta(days=1)
    ayer = hoy - timedelta(days=1)

    tramos_hoy = {t.hora: t.precio for t in precios_dia.tramos}
    tramos_manana = {h: p for h, p in repo.obtener_precios_fecha(manana)} if repo.obtener_precios_fecha(manana) else {}
    tramos_ayer = {h: p for h, p in repo.obtener_precios_fecha(ayer)} if repo.obtener_precios_fecha(ayer) else {}

    horas_antes, horas_despues = 3, 3
    horas = []
    for h_offset in range(-horas_antes, horas_despues + 1):
        h_abs = hora_actual + h_offset
        if h_abs < 0:
            h_display = 24 + h_abs
            dia_tramos = tramos_ayer
        elif h_abs <= 23:
            dia_tramos = tramos_hoy
            h_display = h_abs
        else:
            dia_tramos = tramos_manana
            h_display = h_abs - 24
        if h_display in dia_tramos:
            horas.append((h_display, dia_tramos[h_display]))
    return horas


def _get_price_emoji(
    precio: float,
    _precios_lista: list[float] | None = None,
    fecha: date | None = None,
) -> str:
    f = fecha or _fecha_hoy()
    bajo, alto = get_umbrales_fecha(f)
    if precio <= bajo:
        return "🟢"
    if precio >= alto:
        return "🔴"
    return "🟡"


def _formatear_tabla_inteligente(horas_precios: list[tuple[int, float]], hora_actual: int) -> str:
    hoy = _fecha_hoy()
    manana = hoy + timedelta(days=1)
    ayer = hoy - timedelta(days=1)

    precios_vals = [p for _, p in horas_precios]
    min_p = min(precios_vals)
    max_p = max(precios_vals)
    avg_p = sum(precios_vals) / len(precios_vals)

    lineas = [
        "⚡️ <b>Precios alrededor de ahora</b>",
        "",
        f"📍 <b>Hora:</b> {hora_actual:02d}:00",
        f"📊 <b>Rango:</b> 🟢 {min_p:.3f} → 🔴 {max_p:.3f} €/kWh",
        f"📈 <b>Media:</b> 🟡 {avg_p:.3f} €/kWh",
        "",
    ]
    for h, p in horas_precios:
        if hora_actual >= 21 and h <= 2:
            dia_ref = manana
        elif hora_actual <= 2 and h >= 21:
            dia_ref = ayer
        else:
            dia_ref = hoy
        emoji = _get_price_emoji(p, precios_vals, dia_ref)
        marcador = " <i>(mañana)</i>" if dia_ref == manana else (" <i>(ayer)</i>" if dia_ref == ayer else "")
        if h == hora_actual:
            lineas.append(f"{emoji} <b>{h:02d}:00</b>   <b>{p:.3f}</b> €/kWh   ⬅️ <i>AHORA</i>{marcador}")
        else:
            lineas.append(f"{emoji} {h:02d}:00   {p:.3f} €/kWh{marcador}")
    return "\n".join(lineas)


def _resumen_dia(precios: PreciosDia, label: str = "") -> str:
    t = precios.tramos_ordenados()
    if not t:
        return "No hay datos disponibles."
    min_precio = min(t, key=lambda x: x.precio)
    max_precio = max(t, key=lambda x: x.precio)
    precios_vals = [tr.precio for tr in t]
    lineas = [
        f"⚡️ <b>Precios del día {label}</b>",
        f"📅 {precios.fecha}",
        "",
        "<b>📊 Resumen</b>",
        f"🟢 <b>Más barato:</b> {min_precio.precio:.3f} €/kWh a las {min_precio.hora:02d}:00",
        f"🔴 <b>Más caro:</b> {max_precio.precio:.3f} €/kWh a las {max_precio.hora:02d}:00",
        f"🟡 <b>Media:</b> {precios.media:.3f} €/kWh",
        "",
        "<b>🕐 Desglose por hora</b>",
    ]
    for tramo in t:
        emoji = _get_price_emoji(tramo.precio, precios_vals, precios.fecha)
        lineas.append(f"{emoji} {tramo.hora:02d}:00   <b>{tramo.precio:.3f}</b> €/kWh")
    lineas.append("")
    lineas.append("<i>Leyenda: 🟢 barato  🟡 medio  🔴 caro</i>")
    return "\n".join(lineas)


@router.message(CommandStart())
async def cmd_start(message: Message):
    if await _reject_if_not_allowed(message):
        return
    await message.answer(
        "⚡️ Bot de precios de la luz (PVPC)\n\n"
        "Usa /help para ver todos los comandos."
    )


@router.message(Command("help"))
@router.message(Command("ayuda"))
async def cmd_help(message: Message):
    if await _reject_if_not_allowed(message):
        return
    ayuda_text = (
        "⚡️ <b>BOT DE PRECIOS DE LA LUZ - AYUDA</b>\n\n"
        "<b>📊 CONSULTA:</b>\n"
        "<code>/price</code> — Precios alrededor de ahora\n"
        "<code>/today</code> — Resumen de hoy\n"
        "<code>/tomorrow</code> — Resumen de mañana\n\n"
        "<i>Escribe / en el chat para ver los comandos.</i>"
    )
    await message.answer(ayuda_text, parse_mode="HTML")


@router.message(Command("price"))
async def cmd_price(message: Message):
    if await _reject_if_not_allowed(message):
        return
    hoy = _fecha_hoy()
    tramos = repo.obtener_precios_fecha(hoy)
    if not tramos:
        await message.answer("No hay precios guardados para hoy. Usa /fetchtoday o espera al job diario.")
        return
    precios_dia = PreciosDia(fecha=hoy, tramos=[TramoPrecio(hora=h, precio=p) for h, p in tramos])
    hora_actual = _hora_actual()
    horas_precios = _get_smart_time_range(hora_actual, precios_dia)
    await message.answer(_formatear_tabla_inteligente(horas_precios, hora_actual), parse_mode="HTML")


@router.message(Command("today"))
async def cmd_today(message: Message):
    if await _reject_if_not_allowed(message):
        return
    hoy = _fecha_hoy()
    tramos = repo.obtener_precios_fecha(hoy)
    if not tramos:
        await message.answer("No hay precios guardados para hoy. Usa /fetchtoday o espera al job diario.")
        return
    precios = PreciosDia(fecha=hoy, tramos=[TramoPrecio(hora=h, precio=p) for h, p in tramos])
    await message.answer(_resumen_dia(precios, "(hoy)"), parse_mode="HTML")


@router.message(Command("tomorrow"))
async def cmd_tomorrow(message: Message):
    if await _reject_if_not_allowed(message):
        return
    manana = _fecha_hoy() + timedelta(days=1)
    tramos = repo.obtener_precios_fecha(manana)
    if not tramos:
        await message.answer("No hay precios guardados para mañana. Usa /fetchtomorrow o espera al job diario.")
        return
    precios = PreciosDia(fecha=manana, tramos=[TramoPrecio(hora=h, precio=p) for h, p in tramos])
    await message.answer(_resumen_dia(precios, "(mañana)"), parse_mode="HTML")


@router.message(Command("fetchtoday"))
async def cmd_fetchtoday(message: Message):
    if await _reject_if_not_allowed(message):
        return
    hoy = _fecha_hoy()
    manana = hoy + timedelta(days=1)
    await message.answer("⏳ Obteniendo precios de hoy...")
    precios, web_date = fetch_precios_dia(hoy)
    if not precios:
        if web_date is not None and web_date != hoy:
            repo.borrar_precios_fecha(manana)
            await message.answer(
                f"⏳ Todavía no hay datos para hoy. La web muestra fecha {web_date.strftime('%d/%m/%Y')}. "
                "Se han borrado los precios de mañana por si estaban mal."
            )
        else:
            await message.answer("❌ Error: no se pudieron obtener los precios (revisa la web o la conexión).")
        return
    repo.guardar_precios_dia(precios.fecha, [(t.hora, t.precio) for t in precios.tramos_ordenados()])
    n = len(precios.tramos)
    await message.answer(
        f"✅ Precios de hoy obtenidos y guardados.\n"
        f"Mín: {precios.min_precio:.4f} | Máx: {precios.max_precio:.4f} | Horas: {n}"
    )


@router.message(Command("fetchtomorrow"))
async def cmd_fetchtomorrow(message: Message):
    if await _reject_if_not_allowed(message):
        return
    manana = _fecha_hoy() + timedelta(days=1)
    await message.answer(f"⏳ Obteniendo precios de mañana ({manana.strftime('%d/%m/%Y')}) desde la web...")
    precios, web_date = fetch_precios_dia(manana)
    if not precios:
        if web_date is not None and web_date != manana:
            await message.answer(
                f"⏳ Todavía no hay datos para mañana. La web muestra fecha {web_date.strftime('%d/%m/%Y')}."
            )
        else:
            await message.answer("❌ Error: no se pudieron obtener los precios (revisa la web o la conexión).")
        return
    repo.guardar_precios_dia(precios.fecha, [(t.hora, t.precio) for t in precios.tramos_ordenados()])
    n = len(precios.tramos)
    await message.answer(
        f"✅ Precios de mañana obtenidos y guardados.\n"
        f"Mín: {precios.min_precio:.4f} | Máx: {precios.max_precio:.4f} | Horas: {n}"
    )


@router.message(F.text)
async def catch_all(message: Message):
    if await _reject_if_not_allowed(message):
        return
    text = (message.text or "").strip()
    if text.startswith("/"):
        await message.answer("Comando no reconocido. Escribe /help para ver los comandos disponibles.")
    else:
        await message.answer("Escribe /help para ver los comandos del bot.")
