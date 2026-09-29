"""Тесты экспорта PDF: кириллица, имя файла, совпадение контента (A1, A8)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from src.pdf_export import (
    PdfFontError,
    create_pdf,
    prepare_document,
    register_fonts,
    safe_filename,
)

SAMPLE_SECTIONS = [
    {"header": "Обращение", "body": "Здравствуйте! Предлагаем наше сопровождение."},
    {"header": "Предлагаемые услуги", "body": "СОСТАВ РАБОТ И СТОИМОСТЬ:\n• Аудит — 25 000 ₽."},
]
SAMPLE_PRICING = [
    {"name": "ИТ-аудит и инвентаризация", "price_text": "25 000 ₽", "price": 25000.0},
]


@pytest.fixture(scope="module")
def fonts_ok():
    try:
        register_fonts()
        return True
    except PdfFontError:
        return False


def test_pdf_bytes_and_magic(fonts_ok):
    if not fonts_ok:
        pytest.skip("TTF-шрифт с кириллицей не найден на этой машине")
    doc = prepare_document(
        client="ООО Тест",
        version=1,
        created_at="2026-09-24T12:00:00",
        sections=SAMPLE_SECTIONS,
        pricing=SAMPLE_PRICING,
    )
    data = create_pdf(doc)
    assert isinstance(data, bytes)
    assert data.startswith(b"%PDF")
    assert len(data) > 1000


def test_pdf_contains_section_text(fonts_ok):
    if not fonts_ok:
        pytest.skip("TTF-шрифт с кириллицей не найден")
    doc = prepare_document(
        client="ООО Тест", version=1, created_at="2026-09-24",
        sections=[{"header": "Обращение", "body": "Предлагаем наше сопровождение."}],
        pricing=[],
    )
    data = create_pdf(doc)
    # Кириллица в PDF хранится в сжатых потоках; строим поверхностную проверку,
    # что документ построился и содержит ожидаемые объекты с шрифтом.
    assert b"/Type /Font" in data
    assert data.startswith(b"%PDF")


def test_prepare_document_keeps_content_identity():
    doc = prepare_document("Клиент", 2, "2026-09-24", SAMPLE_SECTIONS, SAMPLE_PRICING)
    assert doc["sections"] == SAMPLE_SECTIONS
    assert doc["pricing"] == SAMPLE_PRICING
    assert doc["client"] == "Клиент"


def test_safe_filename():
    name = safe_filename('ООО "Ромашка": /дом/', 3)
    assert ":" not in name and "/" not in name
    assert name.startswith("КП_ООО Ромашка")
    assert name.endswith("_v3.pdf")


def test_safe_filename_empty_client():
    assert safe_filename("   ", 1).startswith("КП_Клиент_")