#!/usr/bin/env python3
"""Crear tablas de la base de datos."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.storage.repository import init_db

if __name__ == "__main__":
    init_db()
    print("Tablas creadas correctamente.")
