"""Бриф: модель данных и валидация обязательных полей."""
from __future__ import annotations

from dataclasses import dataclass, field

REQUIRED_FIELDS = [
    ("client", "Клиент"),
    ("task", "Задача клиента"),
    ("service_ids", "Услуги"),
    ("deadline", "Сроки"),
]


@dataclass
class Brief:
    client: str = ""
    task: str = ""
    service_ids: list[int] = field(default_factory=list)
    deadline: str = ""
    budget: str = ""
    id: int | None = None


def validate(brief: Brief) -> list[str]:
    """Возвращает список понятных ошибок валидации. Пустой список — ОК.

    Валидация вызывается ДО отправки запроса к ИИ (критерий A5).
    ИИ не вызывается, если список ошибок не пуст.
    """
    errors: list[str] = []
    if not brief.client.strip():
        errors.append("Укажите клиента (название компании).")
    if not brief.task.strip():
        errors.append("Опишите задачу клиента.")
    if not brief.service_ids:
        errors.append("Выберите хотя бы одну услугу из прайса.")
    if not brief.deadline.strip():
        errors.append("Укажите сроки.")
    if not brief.budget.strip():
        # Бюджет опционален (ТЗ FR-1): ничего не делаем.
        pass
    elif len(brief.budget.strip()) > 200:
        errors.append("Поле «Бюджет» слишком длинное (максимум 200 символов).")
    return errors