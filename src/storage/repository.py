"""Almacenamiento: historial de precios, alertas programadas, modelo por chat."""
import os
import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

from config.settings import DB_PATH


def _db_path() -> Path:
    return Path(os.getenv("DB_PATH", str(DB_PATH)))


def get_connection() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Crear tablas si no existen."""
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS precios_historico (
                fecha DATE NOT NULL,
                hora INTEGER NOT NULL,
                precio_real REAL NOT NULL,
                PRIMARY KEY (fecha, hora)
            );
            CREATE TABLE IF NOT EXISTS alertas_programadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha DATE NOT NULL,
                hora_envio TEXT NOT NULL,
                tipo TEXT NOT NULL,
                mensaje TEXT NOT NULL,
                enviado INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS modelo_por_chat (
                chat_id TEXT PRIMARY KEY,
                modelo TEXT NOT NULL,
                actualizado_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS preferencias_chat (
                chat_id TEXT PRIMARY KEY,
                notificaciones INTEGER NOT NULL DEFAULT 1,
                actualizado_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS quota_ia_chat (
                chat_id TEXT PRIMARY KEY,
                usos INTEGER NOT NULL DEFAULT 0
            );
        """)
        conn.commit()
    finally:
        conn.close()


def borrar_precios_fecha(fecha: date) -> None:
    """Elimina todos los tramos guardados para una fecha (p. ej. mañana si la web no tiene datos)."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM precios_historico WHERE fecha = ?", (fecha.isoformat(),))
        conn.commit()
    finally:
        conn.close()


def guardar_precios_dia(fecha: date, tramos: list[tuple[int, float]]) -> None:
    """Guardar 24 tramos (hora 0-23, precio €/kWh) para una fecha."""
    conn = get_connection()
    try:
        conn.executemany(
            "INSERT OR REPLACE INTO precios_historico (fecha, hora, precio_real) VALUES (?, ?, ?)",
            [(fecha.isoformat(), h, p) for h, p in tramos],
        )
        conn.commit()
    finally:
        conn.close()


def obtener_precios_fecha(fecha: date) -> list[tuple[int, float]]:
    """Obtener tramos (hora, precio) para una fecha. Ordenados por hora 0-23."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT hora, precio_real FROM precios_historico WHERE fecha = ? ORDER BY hora",
            (fecha.isoformat(),),
        )
        return [(r["hora"], r["precio_real"]) for r in cur.fetchall()]
    finally:
        conn.close()


def contar_tramos_fecha(fecha: date) -> int:
    """Número de tramos guardados para una fecha."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT COUNT(*) as n FROM precios_historico WHERE fecha = ?",
            (fecha.isoformat(),),
        )
        return cur.fetchone()["n"]
    finally:
        conn.close()


def guardar_alertas_programadas(fecha: date, alertas: list[tuple[str, str, str]]) -> None:
    """Guardar alertas: lista de (hora_envio, tipo, mensaje). Borra las del día primero."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM alertas_programadas WHERE fecha = ?", (fecha.isoformat(),))
        conn.executemany(
            "INSERT INTO alertas_programadas (fecha, hora_envio, tipo, mensaje) VALUES (?, ?, ?, ?)",
            [(fecha.isoformat(), h, t, m) for h, t, m in alertas],
        )
        conn.commit()
    finally:
        conn.close()


def obtener_alertas_pendientes_hora(fecha: date, hora_envio: str) -> list[dict]:
    """Alertas programadas para una fecha y hora de envío, no enviadas."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """SELECT id, mensaje FROM alertas_programadas
               WHERE fecha = ? AND hora_envio = ? AND enviado = 0""",
            (fecha.isoformat(), hora_envio),
        )
        return [{"id": r["id"], "mensaje": r["mensaje"]} for r in cur.fetchall()]
    finally:
        conn.close()


def obtener_alertas_dia(fecha: date) -> list[dict]:
    """Obtiene TODAS las alertas programadas para una fecha (enviadas o no)."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """SELECT id, fecha, hora_envio, tipo, mensaje, enviado 
               FROM alertas_programadas WHERE fecha = ? ORDER BY hora_envio""",
            (fecha.isoformat(),),
        )
        return [
            {
                "id": r["id"],
                "fecha": r["fecha"],
                "hora_envio": r["hora_envio"],
                "tipo": r["tipo"],
                "mensaje": r["mensaje"],
                "enviado": bool(r["enviado"]),
            }
            for r in cur.fetchall()
        ]
    finally:
        conn.close()


def marcar_alerta_enviada(alerta_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE alertas_programadas SET enviado = 1 WHERE id = ?", (alerta_id,))
        conn.commit()
    finally:
        conn.close()


def get_modelo_chat(chat_id: str) -> Optional[str]:
    """Modelo elegido para este chat_id, o None si usa el por defecto."""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT modelo FROM modelo_por_chat WHERE chat_id = ?", (str(chat_id),))
        row = cur.fetchone()
        return row["modelo"] if row else None
    finally:
        conn.close()


def set_modelo_chat(chat_id: str, modelo: str) -> None:
    from datetime import datetime, timezone
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO modelo_por_chat (chat_id, modelo, actualizado_at) VALUES (?, ?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET modelo = ?, actualizado_at = ?""",
            (str(chat_id), modelo, now, modelo, now),
        )
        conn.commit()
    finally:
        conn.close()


def get_notificaciones_chat(chat_id: str) -> bool:
    """True si el chat tiene notificaciones activadas (default: True)."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT notificaciones FROM preferencias_chat WHERE chat_id = ?",
            (str(chat_id),),
        )
        row = cur.fetchone()
        return bool(row["notificaciones"]) if row else True
    finally:
        conn.close()


def set_notificaciones_chat(chat_id: str, activas: bool) -> None:
    from datetime import datetime, timezone
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO preferencias_chat (chat_id, notificaciones, actualizado_at)
               VALUES (?, ?, ?)
               ON CONFLICT(chat_id) DO UPDATE
               SET notificaciones = excluded.notificaciones,
                   actualizado_at = excluded.actualizado_at""",
            (str(chat_id), int(activas), now),
        )
        conn.commit()
    finally:
        conn.close()


def obtener_proxima_alerta_pendiente(fecha: date, hora_actual: str) -> Optional[dict]:
    """Primera alerta pendiente para 'fecha' con hora_envio > hora_actual. None si no hay."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """SELECT id, hora_envio, tipo, mensaje
               FROM alertas_programadas
               WHERE fecha = ? AND enviado = 0 AND hora_envio > ?
               ORDER BY hora_envio
               LIMIT 1""",
            (fecha.isoformat(), hora_actual),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "hora_envio": row["hora_envio"],
            "tipo": row["tipo"],
            "mensaje": row["mensaje"],
        }
    finally:
        conn.close()


def registrar_usuario_si_nuevo(chat_id: str, es_admin: bool) -> None:
    """Inserta en preferencias_chat si no existe fila. Admin=notif ON, público=notif OFF."""
    from datetime import datetime, timezone
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO preferencias_chat (chat_id, notificaciones, actualizado_at) VALUES (?, ?, ?)",
            (str(chat_id), int(es_admin), now),
        )
        conn.commit()
    finally:
        conn.close()


def get_usos_ia(chat_id: str) -> int:
    """Número de consultas IA vitalicias del usuario (0 si no hay registro)."""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT usos FROM quota_ia_chat WHERE chat_id = ?", (str(chat_id),))
        row = cur.fetchone()
        return row["usos"] if row else 0
    finally:
        conn.close()


def incrementar_usos_ia(chat_id: str) -> int:
    """Incrementa el contador vitalicio de IA del usuario. Devuelve el nuevo total."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO quota_ia_chat (chat_id, usos) VALUES (?, 0)", (str(chat_id),)
        )
        conn.execute(
            "UPDATE quota_ia_chat SET usos = usos + 1 WHERE chat_id = ?", (str(chat_id),)
        )
        conn.commit()
        cur = conn.execute("SELECT usos FROM quota_ia_chat WHERE chat_id = ?", (str(chat_id),))
        return cur.fetchone()["usos"]
    finally:
        conn.close()


def obtener_chats_con_notificaciones_activas() -> list[str]:
    """Todos los chat_ids con notificaciones explícitamente activadas (notificaciones=1)."""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT chat_id FROM preferencias_chat WHERE notificaciones = 1")
        return [r["chat_id"] for r in cur.fetchall()]
    finally:
        conn.close()


def obtener_todos_los_chat_ids() -> list[str]:
    """Todos los chat_ids registrados en preferencias_chat."""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT chat_id FROM preferencias_chat")
        return [r["chat_id"] for r in cur.fetchall()]
    finally:
        conn.close()
