"""Tests del módulo de precios."""
from datetime import date

import pytest

from src.precios.models import TramoPrecio, PreciosDia


def test_precios_dia_min_max_media():
    tramos = [TramoPrecio(h, 0.10 + (h % 5) * 0.05) for h in range(24)]
    dia = PreciosDia(fecha=date(2026, 3, 6), tramos=tramos)
    assert dia.min_precio >= 0.10
    assert dia.max_precio <= 0.35
    assert 0.10 <= dia.media <= 0.35


def test_precio_hora():
    tramos = [TramoPrecio(10, 0.25)]
    dia = PreciosDia(fecha=date(2026, 3, 6), tramos=tramos)
    assert dia.precio_hora(10) == 0.25
    assert dia.precio_hora(11) is None
