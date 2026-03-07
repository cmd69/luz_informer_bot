"""Configuración desde variables de entorno."""
import os
from datetime import date
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_IDS: list[str] = [
    x.strip() for x in os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if x.strip()
]

# Precios - fuente configurable
PRECIO_LUZ_FUENTE: str = os.getenv("PRECIO_LUZ_FUENTE", "tarifaluzhora")
TARIFALUZHORA_URL: str = os.getenv("TARIFALUZHORA_URL", "https://tarifaluzhora.es/")

# LLM (Ollama)
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://192.168.1.52:11434/v1/")
LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3.2")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "ollama")
LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))

# Umbrales (€/kWh): entre semana
PRECIO_UMBRAL_BAJO: float = float(os.getenv("PRECIO_UMBRAL_BAJO", "0.12"))
PRECIO_UMBRAL_ALTO: float = float(os.getenv("PRECIO_UMBRAL_ALTO", "0.25"))
# Fin de semana: precios más bajos → umbral verde más bajo, rojo más bajo
PRECIO_UMBRAL_BAJO_FINDE: float = float(os.getenv("PRECIO_UMBRAL_BAJO_FINDE", "0.105"))
PRECIO_UMBRAL_ALTO_FINDE: float = float(os.getenv("PRECIO_UMBRAL_ALTO_FINDE", "0.17"))


def get_umbrales_fecha(f: date) -> Tuple[float, float]:
    """Devuelve (umbral_bajo, umbral_alto) según la fecha: fin de semana usa umbrales más bajos."""
    if f.weekday() in (5, 6):  # sábado, domingo
        return (PRECIO_UMBRAL_BAJO_FINDE, PRECIO_UMBRAL_ALTO_FINDE)
    return (PRECIO_UMBRAL_BAJO, PRECIO_UMBRAL_ALTO)

# Zona horaria
TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Madrid")

# Franja horaria de notificaciones (solo se generan y envían alertas en esta ventana)
# Hora en 0-24: INICIO inclusive, FIN exclusive. Default 7-24 = de 7:00 a 24:00 (medianoche)
ALERTAS_HORA_INICIO: int = int(os.getenv("ALERTAS_HORA_INICIO", "7"))
ALERTAS_HORA_FIN: int = int(os.getenv("ALERTAS_HORA_FIN", "24"))


def hora_en_franja_notificacion(hora: int) -> bool:
    """True si la hora (0-23) está dentro de la franja en la que se notifica."""
    if ALERTAS_HORA_FIN <= ALERTAS_HORA_INICIO:
        # Ej. 22 a 6: franja nocturna
        return hora >= ALERTAS_HORA_INICIO or hora < ALERTAS_HORA_FIN
    return ALERTAS_HORA_INICIO <= hora < ALERTAS_HORA_FIN

# Base de datos
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH: Path = Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "precio_luz.db")))
