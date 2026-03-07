"""Tests de configuración."""
from datetime import date

from config.settings import get_umbrales_fecha, hora_en_franja_notificacion


def test_get_umbrales_fecha_weekday():
    # Lunes 2026-03-09
    bajo, alto = get_umbrales_fecha(date(2026, 3, 9))
    assert bajo == 0.12
    assert alto == 0.25


def test_get_umbrales_fecha_weekend():
    bajo, alto = get_umbrales_fecha(date(2026, 3, 8))  # domingo
    assert bajo == 0.105
    assert alto == 0.17


def test_hora_en_franja_notificacion():
    assert hora_en_franja_notificacion(7) is True
    assert hora_en_franja_notificacion(12) is True
    assert hora_en_franja_notificacion(23) is True
    assert hora_en_franja_notificacion(3) is False
