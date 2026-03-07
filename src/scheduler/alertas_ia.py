"""
Generación de mensajes de alerta del día (sin IA).
- Aviso previo (30 min antes): solo cabecera con franja horaria 🟢/🟠.
- Aviso al inicio de franja: cabecera + tabla de precios.
- Si se pasa on_alert (async), se invoca por cada alerta generada para enviar en vivo.
"""
from datetime import date, datetime
from typing import Awaitable, Callable, Optional
from zoneinfo import ZoneInfo

from config.settings import TIMEZONE, get_umbrales_fecha, hora_en_franja_notificacion
from src.storage import repository as repo

TZ = ZoneInfo(TIMEZONE)


def _precios_texto(fecha: date) -> str:
    tramos = repo.obtener_precios_fecha(fecha)
    if not tramos:
        return ""
    tramos.sort(key=lambda x: x[0])
    return "\n".join(f"{h:02d}:00 - {p:.4f} €/kWh" for h, p in tramos)


def _zonas_dia(fecha: date) -> list[tuple[int, str]]:
    """Para cada hora en franja 7:00-02:00, devuelve (hora, 'verde'|'naranja'|'neutro')."""
    tramos = repo.obtener_precios_fecha(fecha)
    if not tramos:
        return []
    bajo, alto = get_umbrales_fecha(fecha)
    d = dict(tramos)
    horas_franja = list(range(7, 24)) + list(range(0, 3))
    out = []
    for h in horas_franja:
        p = d.get(h, 0)
        if p <= bajo:
            out.append((h, "verde"))
        elif p >= alto:
            out.append((h, "naranja"))
        else:
            out.append((h, "neutro"))
    return out


def _cabecera_franja(verde: bool, hora_inicio: int, hora_fin: int) -> str:
    h_i = f"{hora_inicio:02d}:00"
    h_f = "24:00" if hora_fin == 24 or (hora_fin == 0 and hora_inicio > 12) else f"{hora_fin:02d}:00"
    if verde:
        return f"🟢 <b>FRANJA BARATA</b> · {h_i} – {h_f}"
    return f"🟠 <b>FRANJA CARA</b> · {h_i} – {h_f}"


def _emoji_precio(precio: float, umbral_bajo: float, umbral_alto: float) -> str:
    if precio <= umbral_bajo:
        return "🟢"
    if precio >= umbral_alto:
        return "🔴"
    return "🟡"


def _horas_en_franja(hora_inicio: int, hora_fin: int) -> list[int]:
    if hora_fin == 24:
        return list(range(hora_inicio, 24))
    if hora_inicio < hora_fin:
        return list(range(hora_inicio, hora_fin))
    return list(range(hora_inicio, 24)) + list(range(0, hora_fin))


def _tabla_franja(fecha: date, hora_inicio: int, hora_fin: int) -> str:
    tramos = repo.obtener_precios_fecha(fecha)
    if not tramos:
        return ""
    bajo, alto = get_umbrales_fecha(fecha)
    d = dict(tramos)
    horas = _horas_en_franja(hora_inicio, hora_fin)
    lineas = []
    for h in horas:
        p = d.get(h, 0.0)
        emoji = _emoji_precio(p, bajo, alto)
        lineas.append(f"{emoji} {h:02d}:00   {p:.3f} €/kWh")
    return "\n".join(lineas)


def _mensaje_aviso_previo(verde: bool, hora_inicio: int, hora_fin: int) -> str:
    return _cabecera_franja(verde, hora_inicio, hora_fin)


def _mensaje_aviso_inicio(fecha: date, verde: bool, hora_inicio: int, hora_fin: int) -> str:
    cabecera = _cabecera_franja(verde, hora_inicio, hora_fin)
    tabla = _tabla_franja(fecha, hora_inicio, hora_fin)
    if not tabla:
        return cabecera
    return f"{cabecera}\n\n{tabla}"


def _hora_desde_hora_envio(hora_envio: str) -> int:
    part = hora_envio.strip().split(":")[0]
    try:
        return int(part) % 24
    except ValueError:
        return -1


async def generar_alertas_dia(
    fecha: date,
    on_alert: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
) -> list[tuple[str, str, str]]:
    """
    Genera la lista de alertas programadas para el día: (hora_envio, tipo, mensaje).
    Solo se incluyen alertas cuya hora de envío está dentro de la franja de notificación.
    """
    zonas = _zonas_dia(fecha)
    if not zonas:
        return []
    if not _precios_texto(fecha):
        return []
    alertas: list[tuple[str, str, str]] = []
    i = 0
    while i < len(zonas):
        h, z = zonas[i]
        if z == "verde":
            j = i
            while j < len(zonas) and zonas[j][1] == "verde":
                j += 1
            h_fin_val = (zonas[j - 1][0] + 1) if j > 0 else (h + 1)
            hora_envio_antes = f"{(h-1+24)%24:02d}:30"
            if hora_en_franja_notificacion(_hora_desde_hora_envio(hora_envio_antes)):
                msg_antes = _mensaje_aviso_previo(True, h, h_fin_val)
                alertas.append((hora_envio_antes, "verde_antes", msg_antes))
                if on_alert:
                    await on_alert(hora_envio_antes, "verde_antes", msg_antes)
            if hora_en_franja_notificacion(h):
                msg_inicio = _mensaje_aviso_inicio(fecha, True, h, h_fin_val)
                alertas.append((f"{h:02d}:00", "verde_inicio", msg_inicio))
                if on_alert:
                    await on_alert(f"{h:02d}:00", "verde_inicio", msg_inicio)
            i = j
        elif z == "naranja":
            j = i
            while j < len(zonas) and zonas[j][1] == "naranja":
                j += 1
            h_fin_val = (zonas[j - 1][0] + 1) if j > 0 else (h + 1)
            hora_envio_antes = f"{(h-1+24)%24:02d}:30"
            if hora_en_franja_notificacion(_hora_desde_hora_envio(hora_envio_antes)):
                msg_antes = _mensaje_aviso_previo(False, h, h_fin_val)
                alertas.append((hora_envio_antes, "naranja", msg_antes))
                if on_alert:
                    await on_alert(hora_envio_antes, "naranja", msg_antes)
            if hora_en_franja_notificacion(h):
                msg_inicio = _mensaje_aviso_inicio(fecha, False, h, h_fin_val)
                alertas.append((f"{h:02d}:00", "naranja_inicio", msg_inicio))
                if on_alert:
                    await on_alert(f"{h:02d}:00", "naranja_inicio", msg_inicio)
            i = j
        else:
            i += 1
    return alertas


async def job_diseno_alertas() -> None:
    """Tras tener precios del día, genera alertas y las guarda."""
    hoy = datetime.now(TZ).date()
    if repo.contar_tramos_fecha(hoy) < 24:
        return
    alertas = await generar_alertas_dia(hoy)
    if alertas:
        repo.guardar_alertas_programadas(hoy, alertas)
