"""Pytest fixtures y configuración."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(ROOT / "data" / "test_precio_luz.db"))


@pytest.fixture
def db_path(tmp_path):
    p = tmp_path / "test.db"
    os.environ["DB_PATH"] = str(p)
    return p
