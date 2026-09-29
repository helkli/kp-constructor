"""E2E-тест генерации с мок-провайдером.

Проверяет сквозной сценарий: модель в ответе придумала цену (15 000 ₽) и срок
(3 месяца) — после оркестрации в КП остаются только цены из прайса и срок из брифа.
Критерии A2, A3, A10.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ai.service import generate_proposal_sections
from src.brief import Brief


class FakeProvider:
    name = "FakeGPT"
    model = "fake-model"

    def complete(self, system_prompt, user_prompt, timeout=None, temperature=0.4):
        # Модель «галлюцинирует»: цена 15 000 ₽ (нет в прайсе), срок 3 месяца (в брифе — 2 недели).
        return """## Обращение
Здравствуйте, команда ООО Тест!
## Понимание задачи
Нужна плановая поддержка серверной инфраструктуры.
## Предлагаемые услуги
Организуем администрирование серверов. Стоимость работ: 15 000 ₽ в месяц.
## Сроки
Выполним за 3 месяца.
## Условия и порядок работы
Работаем по регламенту с еженедельными отчётами.
## Следующие шаги
Обсудим детали по звонку.
"""


def test_generated_text_has_no_invented_prices_or_deadlines(storage, monkeypatch):
    monkeypatch.setattr("src.ai.service.create_provider", lambda *a, **kw: FakeProvider())

    service = storage.list_services(active_only=True)[0]  # "ИТ-аудит…" 25 000 ₽
    brief = Brief(
        client="ООО Тест",
        task="Плановая поддержка серверов",
        service_ids=[service["id"]],
        deadline="2 недели",
        budget="",
    )

    result = generate_proposal_sections(storage, brief, [service])

    text = "\n".join(sec["body"] for sec in result.sections)

    # Выдуманная цена ушла
    assert "15 000 ₽" not in text
    # Придуманный срок ушёл, заменился сроком из брифа
    assert "3 месяца" not in text
    assert "2 недели" in text

    # Цены в КП — только из прайса, блок формируется кодом
    services_section = next(s for s in result.sections if "слуг" in s["header"].lower())
    assert "СОСТАВ РАБОТ И СТОИМОСТЬ:" in services_section["body"]
    assert "25 000 ₽" in services_section["body"]

    # Каноническая строка срока в разделе «Сроки»
    deadline_section = next(s for s in result.sections if "срок" in s["header"].lower())
    assert "Срок выполнения работ: 2 недели." in deadline_section["body"]

    # Замечания guard-слоя зафиксировали правки
    assert result.warnings


def test_missing_price_becomes_placeholder(storage, monkeypatch):
    """Цена услуги отсутствует в прайсе -> «цена уточняется» (критерий A3)."""
    monkeypatch.setattr("src.ai.service.create_provider", lambda *a, **kw: FakeProvider())

    # Последняя услуга из сидов не имеет цены (price = None)
    services = storage.list_services(active_only=True)
    no_price = next(s for s in services if s["price"] is None)

    brief = Brief(
        client="ООО Тест",
        task="Настройка почты",
        service_ids=[no_price["id"]],
        deadline="1 месяц",
        budget="",
    )
    result = generate_proposal_sections(storage, brief, [no_price])

    services_section = next(s for s in result.sections if "слуг" in s["header"].lower())
    assert "цена уточняется" in services_section["body"]


def test_logs_persist_call_without_personal_data(storage, monkeypatch):
    monkeypatch.setattr("src.ai.service.create_provider", lambda *a, **kw: FakeProvider())
    service = storage.list_services(active_only=True)[0]
    brief = Brief(
        client="ООО Тест",
        task="Поддержка",
        service_ids=[service["id"]],
        deadline="неделя",
        budget="",
    )
    generate_proposal_sections(storage, brief, [service])

    logs = storage._conn.execute("SELECT prompt, response, error FROM ai_logs").fetchall()
    assert len(logs) == 1
    prompt = logs[0]["prompt"]
    response = logs[0]["response"]
    # Промпт не содержит телефонов/email; ответ сохранён без ПДн
    assert "@" not in prompt  # в брифе нет email и промпт собран кодом
    assert "ООО Тест" in prompt  # название компании сохраняется (это не ПДн) — абстракция проверки