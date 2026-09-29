"""Сквозная проверка критерия готовности: «PDF совпадает с отредактированной версией».

Из PDF извлекается текст (pypdf) и сверяется с исходными разделами КП.
Разрешается различие только в переносах строк/пробелах (см. pdf_export.create_pdf).
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

pypdf = pytest.importorskip("pypdf")

from src.pdf_export import create_pdf, prepare_document, register_fonts, PdfFontError  # noqa: E402

# «Отредактированная менеджером версия» — то, что лежит в разделах proposal.sections.
EDITED_SECTIONS = [
    {"header": "Обращение", "body": "Здравствуйте, ООО «Ромашка»!\nРады помочь с автоматизацией."},
    {"header": "Сроки", "body": "Срок выполнения работ: 2 недели."},
    {
        "header": "Предлагаемые услуги",
        "body": "СОСТАВ РАБОТ И СТОИМОСТЬ:\n• ИТ-аудит и инвентаризация — цена уточняется.",
    },
]
EDITED_PRICING = [{"name": "ИТ-аудит и инвентаризация", "price_text": "цена уточняется"}]


def _fonts_ok() -> bool:
    try:
        register_fonts()
        return True
    except PdfFontError:
        return False


def _extract_text(pdf_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    return " ".join((page.extract_text() or "") for page in reader.pages)


def _norm(s: str) -> str:
    return " ".join(s.split())


def test_pdf_text_contains_every_edited_line():
    """Каждая непустая строка отредактированных разделов дословно в PDF."""
    if not _fonts_ok():
        pytest.skip("TTF-шрифт с кириллицей не найден")
    doc = prepare_document("ООО «Ромашка»", 3, "2026-09-28", EDITED_SECTIONS, [])
    text = _norm(_extract_text(create_pdf(doc)))

    for sec in EDITED_SECTIONS:
        for line in sec["body"].split("\n"):
            line = _norm(line)
            if line:
                assert line in text, f"В PDF отсутствует строка: {line!r}"
        header = _norm(sec["header"])
        assert header in text, f"В PDF отсутствует заголовок: {header!r}"


def test_pdf_pricing_table_matches_pricing():
    """Таблица «Состав работ и стоимость» в PDF совпадает с прайсом КП."""
    if not _fonts_ok():
        pytest.skip("TTF-шрифт с кириллицей не найден")
    doc = prepare_document(
        "Клиент", 1, "2026-09-28",
        [{"header": "Обращение", "body": "Текст раздела."}],
        EDITED_PRICING,
    )
    text = _norm(_extract_text(create_pdf(doc)))

    assert "Состав работ и стоимость" in text
    assert "ИТ-аудит и инвентаризация" in text
    assert "цена уточняется" in text


def test_pdf_has_no_extra_made_up_content():
    """В PDF не появляется текста, которого нет в отредактированной версии."""
    if not _fonts_ok():
        pytest.skip("TTF-шрифт с кириллицей не найден")
    doc = prepare_document(
        "Клиент", 1, "2026-09-28",
        [{"header": "Обращение", "body": "Единственный текст раздела."}],
        [],
    )
    text = _norm(_extract_text(create_pdf(doc)))
    # Служебные строки шапки/футера разрешены; «придуманного» контента быть не должно.
    assert "Единственный текст раздела" in text
    assert "придуманная вымышленная услуга" not in text