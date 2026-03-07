"""Tests del almacenamiento."""
from datetime import date

import pytest

from src.storage.repository import (
    init_db,
    guardar_precios_dia,
    obtener_precios_fecha,
    contar_tramos_fecha,
    guardar_alertas_programadas,
    obtener_alertas_pendientes_hora,
    marcar_alerta_enviada,
    get_modelo_chat,
    set_modelo_chat,
)


@pytest.fixture(autouse=True)
def _init_db(db_path):
    init_db()


def test_guardar_y_obtener_precios():
    f = date(2026, 3, 6)
    tramos = [(h, 0.10 + h * 0.001) for h in range(24)]
    guardar_precios_dia(f, tramos)
    got = obtener_precios_fecha(f)
    assert len(got) == 24
    assert got[0] == (0, 0.10)
    assert got[23] == (23, 0.123)


def test_contar_tramos():
    f = date(2026, 3, 7)
    assert contar_tramos_fecha(f) == 0
    guardar_precios_dia(f, [(0, 0.1), (1, 0.2)])
    assert contar_tramos_fecha(f) == 2


def test_alertas_programadas():
    f = date(2026, 3, 6)
    guardar_alertas_programadas(f, [
        ("08:30", "verde_antes", "Mensaje 1"),
        ("09:00", "verde_inicio", "Mensaje 2"),
    ])
    pend = obtener_alertas_pendientes_hora(f, "08:30")
    assert len(pend) == 1
    assert pend[0]["mensaje"] == "Mensaje 1"
    marcar_alerta_enviada(pend[0]["id"])
    pend2 = obtener_alertas_pendientes_hora(f, "08:30")
    assert len(pend2) == 0


def test_modelo_por_chat():
    assert get_modelo_chat("123") is None
    set_modelo_chat("123", "llama3.2")
    assert get_modelo_chat("123") == "llama3.2"
