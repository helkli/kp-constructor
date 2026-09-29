"""Guard-тесты: цены (A2/A3), сроки, обезличивание ПДн (A9)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ai.guard import (
    depersonalize,
    ensure_deadline,
    extract_deadline_tokens,
    find_price_violations,
    normalize_amount,
    sanitize_dates_in_text,
    sanitize_prices,
)


# ---------- цены ----------
def test_normalize_amount_variants():
    assert normalize_amount("12 000") == 12000.0
    assert normalize_amount("1500") == 1500.0
    assert normalize_amount("1 500,50") == 1500.5


def test_sanitize_prices_replaces_hallucination():
    text = "Стоимость работ: 15 000 ₽ в месяц и 300 руб за кг."
    clean, fixes = sanitize_prices(text, allowed={12000.0})
    assert "15 000 ₽" not in clean
    assert "цена уточняется" in clean
    assert len(fixes) == 2  # и 15 000 ₽, и 300 руб — не в прайсе


def test_sanitize_prices_keeps_allowed_prices():
    text = "Итого: 12 000 ₽."
    clean, fixes = sanitize_prices(text, allowed={12000.0})
    assert "12 000 ₽" in clean
    assert fixes == []


def test_find_price_violations():
    text = "Ориентир: 999 руб, допустимо 12 000 ₽."
    violations = find_price_violations(text, allowed={12000.0, 5000.0})
    assert len(violations) == 1
    assert violations[0]["amount"] == 999.0


def test_prices_inside_numbers_not_flagged():
    # Даты/годы без признака валюты не трогаем.
    text = "Срок по договору с 2025 года."
    violations = find_price_violations(text, allowed={12000.0})
    assert violations == []


# ---------- сроки ----------
def test_ensure_deadline_replaces_invented_period():
    text = "Выполним за 3 месяца и начнём в январе 2027."
    clean, fixes = ensure_deadline(text, "2 недели")
    assert "3 месяца" not in clean
    assert "2 недели" in clean
    assert fixes


def test_sanitize_dates_without_brief_deadline():
    text = "Приступим к 15.01 и завершим к декабрю 2026."
    clean, fixes = sanitize_dates_in_text(text, "")
    assert "15.01" not in clean
    assert "срок уточняется" in clean
    assert fixes


def test_extract_deadline_tokens():
    text = "Уложимся в 5 дней, старт 01.12."
    tokens = extract_deadline_tokens(text)
    assert "5 дней" in tokens
    assert "01.12" in tokens


# ---------- ПДн ----------
def test_depersonalize_removes_email_and_phone():
    text = "Пишите на ivan@mail.ru или звоните 8 999 123-45-67."
    clean = depersonalize(text)
    assert "ivan@mail.ru" not in clean
    assert "8 999 123-45-67" not in clean
    assert "[e-mail удалён]" in clean


def test_depersonalize_masks_long_document_number():
    text = "Паспорт 1234 567890 и ИНН 770123456789"
    clean = depersonalize(text)
    assert "1234 567890" not in clean
    assert "770123456789" not in clean
    assert "[номер документа удалён]" in clean