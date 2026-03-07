"""Scraping de tarifaluzhora.es para obtener precios PVPC por hora."""
import logging
import re
from datetime import date, datetime
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup

from config.settings import TARIFALUZHORA_URL, TIMEZONE
from src.precios.models import PreciosDia, TramoPrecio

logger = logging.getLogger(__name__)


def _extraer_fecha_web(soup: BeautifulSoup) -> Optional[date]:
    """
    Extrae la fecha del día cuyos precios muestra la web.
    Origen: <h2 class="template-tlh__title">Precio de la luz por horas 07/03/2026 o mañana</h2>.
    Formato en el HTML: DD/MM/YYYY.
    """
    h2 = soup.find("h2", class_="template-tlh__title")
    if not h2:
        return None
    texto = h2.get_text(separator=" ", strip=True)
    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto)
    if not match:
        return None
    try:
        d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return date(y, m, d)
    except (ValueError, TypeError):
        return None


def _parse_precio_texto(texto: str) -> Optional[float]:
    """Extrae número de precio desde texto tipo '0,1085 €/kWh', '0,08 €/kWh' o '0.1289'."""
    texto = texto.replace(",", ".").strip()
    match = re.search(r"(\d+\.?\d*)\s*(?:€|eur|/kWh)?", texto, re.I)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _parse_hora_descripcion(texto: str) -> Optional[int]:
    """Extrae la hora de inicio de texto '00:00 - 01:00' → 0, '20:00 - 21:00' → 20."""
    match = re.match(r"(\d{1,2}):00\s*[-–]\s*\d{1,2}:00", texto.strip())
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def _extraer_tramos_itemprop(soup: BeautifulSoup) -> list[TramoPrecio]:
    """
    Estrategia principal: bloques div.template-tlh__colors--hours con
    span[itemprop="description"] (ej. "00:00 - 01:00") y span[itemprop="price"] (ej. "0,1085 €/kWh").
    """
    tramos: list[TramoPrecio] = []
    blocks = soup.find_all("div", class_="template-tlh__colors--hours")
    for block in blocks:
        desc_span = block.find("span", itemprop="description")
        price_span = block.find("span", itemprop="price")
        if not desc_span or not price_span:
            continue
        hora = _parse_hora_descripcion(desc_span.get_text(strip=True))
        precio = _parse_precio_texto(price_span.get_text(strip=True))
        if hora is not None and precio is not None and 0 <= hora <= 23 and 0.01 < precio < 2.0:
            tramos.append(TramoPrecio(hora=hora, precio=precio))
    return tramos


def _url_para_fecha(fecha: Optional[date]) -> str:
    """
    URL para tarifaluzhora.es: hoy = base; otro día = base/?date=YYYY-MM-DD.
    """
    base = TARIFALUZHORA_URL.rstrip("/")
    if fecha is None:
        return f"{base}/"
    if "?" in base:
        return f"{base}&date={fecha.isoformat()}"
    return f"{base}/?date={fecha.isoformat()}"


def fetch_precios_dia(fecha: Optional[date] = None) -> Tuple[Optional[PreciosDia], Optional[date]]:
    """
    Descarga la página de tarifaluzhora.es y parsea los 24 tramos horarios.
    Si fecha es None, se asume hoy (URL base). Para otro día se usa ?date=YYYY-MM-DD.
    Devuelve (PreciosDia o None, fecha_web o None).
    """
    url = _url_para_fecha(fecha)
    logger.info("Petición precios: fecha_solicitada=%s → URL=%s", fecha, url)
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=15.0)
        resp.raise_for_status()
    except Exception as e:
        logger.error("Error descargando %s: %s", url, e)
        return (None, None)

    soup = BeautifulSoup(resp.text, "html.parser")
    web_date = _extraer_fecha_web(soup)
    tramos = _extraer_tramos_itemprop(soup)

    if len(tramos) < 24:
        logger.warning("Estrategia itemprop encontró %d tramos, intentando fallback.", len(tramos))
        tramos = []
        desc_spans = soup.find_all("span", itemprop="description")
        for span in desc_spans:
            text = span.get_text(strip=True)
            if not re.match(r"\d{1,2}:00\s*[-–]\s*\d{1,2}:00", text):
                continue
            hora = _parse_hora_descripcion(text)
            if hora is None or hora < 0 or hora > 23:
                continue
            parent = span.parent
            for _ in range(5):
                if parent is None:
                    break
                price_span = parent.find("span", itemprop="price")
                if price_span:
                    precio = _parse_precio_texto(price_span.get_text(strip=True))
                    if precio is not None and 0.01 < precio < 2.0:
                        tramos.append(TramoPrecio(hora=hora, precio=precio))
                    break
                parent = parent.parent

    if len(tramos) != 24:
        logger.error("Solo se encontraron %d tramos de 24. Descartando resultado.", len(tramos))
        return (None, web_date)

    horas_presentes = {t.hora for t in tramos}
    if horas_presentes != set(range(24)):
        faltantes = set(range(24)) - horas_presentes
        logger.error("Faltan horas: %s. Descartando resultado.", faltantes)
        return (None, web_date)

    precios_set = {t.precio for t in tramos}
    if len(precios_set) < 12:
        logger.error("Solo %d precios únicos encontrados (mínimo 12 esperados). Descartando.", len(precios_set))
        return (None, web_date)

    tramos_ordenados = sorted(tramos, key=lambda t: t.hora)

    if fecha is None:
        tz = ZoneInfo(TIMEZONE)
        fecha = datetime.now(tz).date()

    if web_date is not None and fecha is not None and web_date != fecha:
        logger.warning(
            "La web muestra fecha %s pero se solicitó %s. No hay datos válidos para el día pedido.",
            web_date, fecha,
        )
        return (None, web_date)

    fecha_final = web_date if web_date is not None else fecha
    logger.info("✅ Precios para %s cargados: %d horas, %d precios únicos", fecha_final, len(tramos), len(precios_set))
    return (PreciosDia(fecha=fecha_final, tramos=tramos_ordenados), web_date)
