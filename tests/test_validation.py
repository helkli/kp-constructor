"""Тесты валидации брифа (критерий A5)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.brief import Brief, validate


def test_empty_brief_fails_all_required_fields():
    errors = validate(Brief(client="  ", task="", service_ids=[], deadline=""))
    assert any("клиент" in e.lower() for e in errors)
    assert any("задач" in e.lower() for e in errors)
    assert any("услуг" in e.lower() for e in errors)
    assert any("срок" in e.lower() for e in errors)


def test_partial_brief_reports_specific_fields():
    errors = validate(Brief(client="ООО Тест", task="", service_ids=[1], deadline="2 недели"))
    assert any("задач" in e.lower() for e in errors)
    assert all("Укажите клиента" not in e for e in errors)
    assert all("выберите хотя бы одну услугу" not in e.lower() for e in errors)


def test_valid_brief_passes():
    brief = Brief(
        client="ООО Ромашка",
        task="Поддержка серверов",
        service_ids=[1, 2],
        deadline="2 недели",
        budget="",
    )
    assert validate(brief) == []


def test_budget_optional_but_too_long_rejected():
    brief = Brief(
        client="Тест", task="Задача", service_ids=[1], deadline="мес", budget="x" * 201
    )
    errors = validate(brief)
    assert any("Бюджет" in e for e in errors)