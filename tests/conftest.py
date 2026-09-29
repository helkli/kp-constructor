"""Общие фикстуры тестов: чистый Storage во временной папке."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from src.storage import Storage


@pytest.fixture()
def storage(tmp_path):
    s = Storage(tmp_path / "test.db")
    yield s
    s.close()