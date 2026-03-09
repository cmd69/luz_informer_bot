"""Telegram handlers: consulta, fetch, alertas."""
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from config.settings import IA_QUOTA_PUBLICA, LLM_MODEL, TELEGRAM_CHAT_IDS, TIMEZONE, get_umbrales_fecha
from src.llm import client as llm_client
from src.precios.models import PreciosDia, TramoPrecio
from src.precios.tarifaluzhora import fetch_precios_dia
from src.scheduler.alertas_ia import generar_alertas_dia
from src.storage import repository as repo

logger = logging.getLogger(__name__)
router = Router()
TZ = ZoneInfo(TIMEZONE)


def _es_admin(chat_id: int) -> bool:
    """True si el chat está en la lista de admins (TELEGRAM_CHAT_IDS)."""
    return str(chat_id) in TELEGRAM_CHAT_IDS


async def _reject_if_not_admin(message: Message) -> bool:
    """Rechaza si el usuario no es admin. Devuelve True si fue rechazado."""
    if _es_admin(message.chat.id):
        return False
    await message.answer("⛔ Este comando es solo para administradores.")
    return True


async def _check_ia_quota(message: Message) -> bool:
    """True si el usuario público ha agotado su cuota vitalicia de IA (admins sin límite)."""
    if _es_admin(message.chat.id):
        return False
    usos = repo.get_usos_ia(str(message.chat.id))
    if usos >= IA_QUOTA_PUBLICA:
        await message.answer(
            f"⚠️ Has agotado tu cuota de <b>{IA_QUOTA_PUBLICA} consultas</b> a la IA.\n\n"
            "Si eres usuario habitual, contacta al administrador para obtener acceso ilimitado.",
            parse_mode="HTML",
        )
        return True
    return False


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
    hora_actual = _hora_actual()
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
        if tramo.hora == hora_actual:
            lineas.append(f"{emoji} {tramo.hora:02d}:00   <b>{tramo.precio:.3f}</b> €/kWh   ⬅️ AHORA")
        else:
            lineas.append(f"{emoji} {tramo.hora:02d}:00   <b>{tramo.precio:.3f}</b> €/kWh")
    lineas.append("")
    lineas.append("<i>Leyenda: 🟢 barato  🟡 medio  🔴 caro</i>")
    return "\n".join(lineas)


# ── Comandos públicos ──────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    es_admin = _es_admin(message.chat.id)
    repo.registrar_usuario_si_nuevo(str(message.chat.id), es_admin)

    if es_admin:
        acceso_txt = "Tienes acceso de <b>administrador</b>: todos los comandos sin límites."
    else:
        acceso_txt = (
            f"Tienes acceso de <b>usuario público</b>:\n"
            f"• Consultas de precios: ilimitadas\n"
            f"• Consultas a la IA (/ask): <b>{IA_QUOTA_PUBLICA} en total</b>\n"
            f"• Alertas automáticas: actívalas con /notificaciones\n"
            f"• Comandos de gestión: solo admins\n\n"
            "Para obtener acceso completo, contacta con el administrador del bot."
        )

    await message.answer(
        "⚡ <b>Bot de precios de la luz (PVPC)</b>\n\n"
        "Consulta los precios de la electricidad en tiempo real y recibe alertas "
        "de las franjas baratas y caras del día.\n\n"
        f"{acceso_txt}\n\n"
        "Usa /help para ver todos los comandos disponibles.",
        parse_mode="HTML",
    )


@router.message(Command("help"))
@router.message(Command("ayuda"))
async def cmd_help(message: Message):
    ayuda_text = (
        "⚡️ <b>BOT DE PRECIOS DE LA LUZ - AYUDA</b>\n\n"
        "<b>📊 CONSULTA:</b>\n"
        "<code>/price</code> — Precios alrededor de ahora\n"
        "<code>/today</code> — Resumen de hoy\n"
        "<code>/tomorrow</code> — Resumen de mañana\n\n"
        "<b>📥 DATOS:</b>\n"
        "<code>/fetchtoday</code> — Descargar precios de hoy\n"
        "<code>/fetchtomorrow</code> — Descargar precios de mañana\n\n"
        "<b>🤖 IA:</b>\n"
        f"<code>/ask</code> &lt;pregunta&gt; — Pregunta sobre precios (cuota: {IA_QUOTA_PUBLICA} consultas)\n"
        "<code>/models</code> — Listar modelos\n"
        "<code>/models</code> &lt;nombre&gt; — Elegir modelo\n"
        "<code>/testollama</code> — Probar conexión Ollama\n\n"
        "<b>🔔 ALERTAS:</b>\n"
        "<code>/generate_alerts</code> — Generar alertas del día\n"
        "<code>/show_alerts</code> — Ver alertas de hoy\n"
        "<code>/test_alerts</code> — Ver próxima alerta pendiente\n"
        "<code>/notificaciones</code> — Activar/desactivar alertas automáticas\n\n"
        "<i>Escribe / en el chat para ver los comandos.</i>"
    )
    await message.answer(ayuda_text, parse_mode="HTML")


@router.message(Command("price"))
async def cmd_price(message: Message):
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
    hoy = _fecha_hoy()
    tramos = repo.obtener_precios_fecha(hoy)
    if not tramos:
        await message.answer("No hay precios guardados para hoy. Usa /fetchtoday o espera al job diario.")
        return
    precios = PreciosDia(fecha=hoy, tramos=[TramoPrecio(hora=h, precio=p) for h, p in tramos])
    await message.answer(_resumen_dia(precios, "(hoy)"), parse_mode="HTML")


@router.message(Command("tomorrow"))
async def cmd_tomorrow(message: Message):
    manana = _fecha_hoy() + timedelta(days=1)
    tramos = repo.obtener_precios_fecha(manana)
    if not tramos:
        await message.answer("No hay precios guardados para mañana. Usa /fetchtomorrow o espera al job diario.")
        return
    precios = PreciosDia(fecha=manana, tramos=[TramoPrecio(hora=h, precio=p) for h, p in tramos])
    await message.answer(_resumen_dia(precios, "(mañana)"), parse_mode="HTML")


@router.message(Command("notificaciones"))
async def cmd_notificaciones(message: Message):
    chat_id = str(message.chat.id)
    repo.registrar_usuario_si_nuevo(chat_id, _es_admin(message.chat.id))
    actual = repo.get_notificaciones_chat(chat_id)
    nuevo = not actual
    repo.set_notificaciones_chat(chat_id, nuevo)
    if nuevo:
        await message.answer(
            "🔔 <b>Notificaciones activadas.</b>\n"
            "Recibirás alertas automáticas de franjas baratas y caras.",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "🔕 <b>Notificaciones desactivadas.</b>\n"
            "Usa /notificaciones para reactivarlas.",
            parse_mode="HTML",
        )


# ── Comandos con cuota IA ──────────────────────────────────────────────────────

@router.message(Command("ask"))
async def cmd_ask(message: Message):
    if await _check_ia_quota(message):
        return
    partes = message.text.split(maxsplit=1)
    pregunta = partes[1].strip() if len(partes) > 1 else ""
    if not pregunta:
        usos = repo.get_usos_ia(str(message.chat.id))
        restantes = max(0, IA_QUOTA_PUBLICA - usos) if not _es_admin(message.chat.id) else "∞"
        await message.answer(
            "Uso: /ask &lt;tu pregunta sobre precios de la luz&gt;\n"
            f"<i>Consultas disponibles: {restantes}</i>",
            parse_mode="HTML",
        )
        return
    hoy = _fecha_hoy()
    manana = hoy + timedelta(days=1)
    ctx_lineas = []
    for f, label in [(hoy, "today"), (manana, "tomorrow")]:
        tramos = repo.obtener_precios_fecha(f)
        if tramos:
            tramos_str = ", ".join([f"{h:02d}:00={p:.3f}" for h, p in tramos])
            ctx_lineas.append(f"{label} (24h in €/kWh): {tramos_str}")
    contexto = "\n".join(ctx_lineas) if ctx_lineas else "Sin datos de precios recientes."
    modelo = repo.get_modelo_chat(str(message.chat.id)) or LLM_MODEL
    try:
        from src.llm.client import chat_completion
        system_prompt = (
            "You are an assistant that answers questions about electricity prices in Spain (PVPC). "
            "You have access to hourly prices for today and tomorrow (format: HH:00=price €/kWh). "
            "Answer in Spanish. If asked about prices not in the context, say you don't have that data."
        )
        resp = chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Price context:\n{contexto}\n\nUser question: {pregunta}"},
            ],
            model=modelo,
            caller="ask",
        )
        await message.answer(resp or "Sin respuesta del modelo.")
        repo.incrementar_usos_ia(str(message.chat.id))
    except Exception as e:
        await message.answer(f"❌ Servicio de consultas no disponible: {e}")


# ── Comandos solo admin ────────────────────────────────────────────────────────

@router.message(Command("fetchtoday"))
async def cmd_fetchtoday(message: Message):
    if await _reject_if_not_admin(message):
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
    if await _reject_if_not_admin(message):
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


@router.message(Command("generate_alerts"))
async def cmd_generate_tips(message: Message):
    if await _reject_if_not_admin(message):
        return
    hoy = _fecha_hoy()
    tramos = repo.obtener_precios_fecha(hoy)
    if len(tramos) < 24:
        await message.answer("⏳ Obteniendo precios de hoy...")
        precios, web_date = fetch_precios_dia(hoy)
        if not precios:
            if web_date is not None and web_date != hoy:
                repo.borrar_precios_fecha(hoy + timedelta(days=1))
                await message.answer(
                    f"⏳ Todavía no hay datos para hoy (la web muestra {web_date.strftime('%d/%m/%Y')})."
                )
            else:
                await message.answer("❌ Error: no se pudieron obtener los precios.")
            return
        repo.guardar_precios_dia(precios.fecha, [(t.hora, t.precio) for t in precios.tramos_ordenados()])
        await message.answer(f"✅ Precios obtenidos: {len(precios.tramos)} horas.")
    await message.answer("📋 Generando alertas del día… Las irás recibiendo en vivo.")

    async def enviar_alerta(_hora: str, _tipo: str, mensaje: str) -> None:
        await message.bot.send_message(chat_id=message.chat.id, text=mensaje)

    alertas = await generar_alertas_dia(hoy, on_alert=enviar_alerta)
    if not alertas:
        await message.answer("⚠️ No se generaron alertas (comprueba si hay precios disponibles).")
        return
    repo.guardar_alertas_programadas(hoy, alertas)
    await message.answer(f"✅ {len(alertas)} alertas generadas y guardadas para hoy.")


@router.message(Command("show_alerts"))
async def cmd_show_alerts(message: Message):
    if await _reject_if_not_admin(message):
        return
    hoy = _fecha_hoy()
    alertas = repo.obtener_alertas_dia(hoy)
    if not alertas:
        await message.answer("📭 No hay alertas para hoy. Usa /generate_alerts para crearlas.")
        return
    lineas = [f"🔔 <b>Alertas para {hoy}</b>", ""]
    for al in alertas:
        estado = "✅" if al["enviado"] else "⏳"
        lineas.append(f"{estado} <b>{al['hora_envio']}</b> [{al['tipo']}]: {al['mensaje']}")
    await message.answer("\n".join(lineas), parse_mode="HTML")


@router.message(Command("test_alerts"))
async def cmd_test_alerts(message: Message):
    if await _reject_if_not_admin(message):
        return
    hoy = _fecha_hoy()
    now = datetime.now(TZ)
    hora_actual_str = f"{now.hour:02d}:{now.minute:02d}"

    alertas_hoy = repo.obtener_alertas_dia(hoy)
    if not alertas_hoy:
        await message.answer(
            "📭 <b>No hay alertas generadas para hoy.</b>\n\n"
            "Usa /generate_alerts para generarlas. El scheduler también las genera automáticamente cada día a las 21:00.",
            parse_mode="HTML",
        )
        return

    proxima = repo.obtener_proxima_alerta_pendiente(hoy, hora_actual_str)
    if proxima:
        await message.answer(
            f"🧪 <b>PRÓXIMA ALERTA PENDIENTE</b>\n\n"
            f"🕐 <b>Hora programada:</b> {proxima['hora_envio']}\n"
            f"📌 <b>Tipo:</b> {proxima['tipo']}\n\n"
            f"{proxima['mensaje']}",
            parse_mode="HTML",
        )
    else:
        total = len(alertas_hoy)
        await message.answer(
            f"✅ <b>Todas las alertas de hoy ya han sido enviadas ({total}).</b>\n\n"
            "Usa /generate_alerts mañana para generar las del día siguiente.",
            parse_mode="HTML",
        )


@router.message(Command("models"), F.text.len() > 7)
async def cmd_models_set(message: Message):
    if await _reject_if_not_admin(message):
        return
    nombre = message.text.split(maxsplit=1)[1].strip()
    repo.set_modelo_chat(str(message.chat.id), nombre)
    await message.answer(f"✅ Modelo elegido: {nombre}")


@router.message(Command("models"))
async def cmd_models_list(message: Message):
    if await _reject_if_not_admin(message):
        return
    modelos = llm_client.list_models()
    if not modelos:
        await message.answer("❌ No se pudo obtener la lista de modelos (¿Ollama accesible?).")
        return
    await message.answer("Modelos disponibles:\n" + "\n".join(f"• {m}" for m in modelos) + "\n\nUsa /models <nombre> para elegir.")


@router.message(Command("testollama"))
async def cmd_test_ollama(message: Message):
    if await _reject_if_not_admin(message):
        return
    ok, msg = llm_client.ollama_health()
    await message.answer(msg)


@router.message(Command("broadcast_start"))
async def cmd_broadcast_start(message: Message):
    if await _reject_if_not_admin(message):
        return

    admin_chat_id = str(message.chat.id)

    # Destinatarios: todos en BD + admins en .env, excluyendo al admin que invoca
    destinatarios: set[str] = set(repo.obtener_todos_los_chat_ids())
    for chat_id in TELEGRAM_CHAT_IDS:
        destinatarios.add(chat_id)
    destinatarios.discard(admin_chat_id)

    if not destinatarios:
        await message.answer("No hay usuarios registrados a quienes enviar el mensaje.")
        return

    await message.answer(f"📢 Enviando mensaje de bienvenida a {len(destinatarios)} usuarios…")

    ok, fail = 0, 0
    for chat_id in destinatarios:
        es_admin = _es_admin(int(chat_id))
        if es_admin:
            acceso_txt = "Tienes acceso de <b>administrador</b>: todos los comandos sin límites."
        else:
            acceso_txt = (
                f"Tienes acceso de <b>usuario público</b>:\n"
                f"• Consultas de precios: ilimitadas\n"
                f"• Consultas a la IA (/ask): <b>{IA_QUOTA_PUBLICA} en total</b>\n"
                f"• Alertas automáticas: actívalas con /notificaciones\n"
                f"• Comandos de gestión: solo admins\n\n"
                "Para obtener acceso completo, contacta con el administrador del bot."
            )
        texto = (
            "⚡ <b>Bot de precios de la luz (PVPC)</b>\n\n"
            "Consulta los precios de la electricidad en tiempo real y recibe alertas "
            "de las franjas baratas y caras del día.\n\n"
            f"{acceso_txt}\n\n"
            "Usa /help para ver todos los comandos disponibles."
        )
        try:
            await message.bot.send_message(chat_id=int(chat_id), text=texto, parse_mode="HTML")
            ok += 1
        except Exception as e:
            logger.warning("broadcast_start: error enviando a chat_id=%s: %s", chat_id, e)
            fail += 1

    resumen = f"✅ Broadcast completado: {ok} enviados"
    if fail:
        resumen += f", {fail} fallidos"
    await message.answer(resumen)


# ── Catch-all ──────────────────────────────────────────────────────────────────

@router.message(F.text)
async def catch_all(message: Message):
    text = (message.text or "").strip()
    if text.startswith("/"):
        await message.answer("Comando no reconocido. Escribe /help para ver los comandos disponibles.")
    else:
        await message.answer("Escribe /help para ver los comandos del bot.")
