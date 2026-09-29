"""Оркестрация генерации КП.

Полный цикл одного раздела/всего КП:
1. сборка промпта (обезличивание ПДн) -> провайдер -> ответ;
2. логирование вызова (без ПДн, с таймингами и ошибками);
3. парсинг разделов, guard-проверка цен и сроков;
4. цены добавляются ТОЛЬКО кодом из прайса (price.py), срок — строкой из брифа.
"""
from __future__ import annotations

import re
import time

from src import config
from src.ai.base import create_provider
from src.ai.errors import AIError, AIResponseError
from src.ai.guard import (
    depersonalize,
    ensure_deadline,
    normalize_amount,
    parse_sections,
    sanitize_dates_in_text,
    sanitize_prices,
)
from src.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from src.logging_util import log_ai_call
from src.price import pricing_block, pricing_rows

_DEADLINE_HEADER_KEY = "срок"
_SERVICE_HEADER_KEY = "услуг"


def services_for_brief_ids(storage, service_ids) -> list[dict]:
    """Услуги по id из брифа (в порядке выбора), берутся из прайса."""
    by_id = {s["id"]: s for s in storage.list_services()}
    return [by_id[sid] for sid in service_ids if sid in by_id]


def _allowed_prices(services: list[dict], budget: str) -> set[float]:
    """Разрешённые суммы: цены из прайса + число из бюджета брифа."""
    allowed = {float(s["price"]) for s in services if s.get("price") is not None}
    m = re.search(r"(?<!\d)\d{1,3}(?:[ \u00A0\u202F']\d{3})*(?:[.,]\d{1,2})?|\d+", budget or "")
    if m:
        allowed.add(normalize_amount(m.group(0)))
    return allowed


def _section_index(sections: list[dict], key: str) -> int | None:
    low = key.lower()
    for i, sec in enumerate(sections):
        if low in sec["header"].lower():
            return i
    return None


def _insert_price_block(sections: list[dict], brief_budget: str, rows: list[dict]) -> None:
    """Вставляет таблицу цен (только из прайса) в раздел про услуги."""
    idx = _section_index(sections, _SERVICE_HEADER_KEY)
    if idx is None:
        idx = 0
    block = pricing_block(rows, budget=brief_budget)
    body = sections[idx]["body"]
    sections[idx]["body"] = (body + "\n\n" + block).strip()


def _apply_deadline(sections: list[dict], deadline: str) -> list[dict]:
    """Каноническая строка срока добавляется кодом; придуманные сроки заменяются."""
    problems: list[dict] = []
    if deadline.strip():
        for sec in sections:
            sec["body"], fixes = ensure_deadline(sec["body"], deadline)
            problems += fixes
        idx = _section_index(sections, _DEADLINE_HEADER_KEY)
        if idx is not None:
            line = f"Срок выполнения работ: {deadline.strip()}."
            body = sections[idx]["body"]
            # ensure_deadline уже мог зафиксировать срок в тексте — не дублируем строку.
            if not re.search(r"срок[а-я]*\s+выполнени[яе]", body, re.IGNORECASE):
                sections[idx]["body"] = (body.rstrip() + "\n\n" + line).strip() if body else line
    else:
        for sec in sections:
            sec["body"], fixes = sanitize_dates_in_text(sec["body"], "")
            problems += fixes
        idx = _section_index(sections, _DEADLINE_HEADER_KEY)
        if idx is not None and not sections[idx]["body"].strip():
            sections[idx]["body"] = "Сроки согласуем отдельно."
    return problems


class GenResult:
    """Итог генерации: разделы КП + таблица цен из прайса."""

    def __init__(self, sections: list[dict], pricing: list[dict], warnings: list[str]):
        self.sections = sections
        self.pricing = pricing
        self.warnings = warnings


def generate_proposal_sections(
    storage,
    brief,
    services: list[dict],
    only_header: str | None = None,
    timeout: float | None = None,
) -> GenResult:
    """Генерирует текст КП. only_header != None — перегенерация одного раздела."""
    template = storage.get_active_template()
    all_sections = template["sections"]
    targets = [s for s in all_sections if s["header"] == only_header] if only_header else all_sections
    if not targets:
        raise AIResponseError("В шаблоне нет раздела с таким заголовком.")

    rows = pricing_rows([s for s in services if s["id"] in brief.service_ids])
    allowed = _allowed_prices(services, brief.budget)
    # Промпт обезличиваем ДО отправки (критерий A9).
    user_prompt = depersonalize(build_user_prompt(brief, targets, services))
    provider = create_provider(config.AI_PROVIDER)

    t0 = time.monotonic()
    try:
        raw = provider.complete(
            SYSTEM_PROMPT, user_prompt, timeout=timeout or config.AI_TIMEOUT
        )
    except AIError as exc:
        duration = int((time.monotonic() - t0) * 1000)
        log_ai_call(storage, provider.name, provider.model, user_prompt, "", duration, error=exc.message)
        raise
    duration = int((time.monotonic() - t0) * 1000)
    log_ai_call(storage, provider.name, provider.model, user_prompt, depersonalize(raw), duration)

    sections = parse_sections(
        raw,
        [s["header"] for s in targets],
        require_all=not bool(only_header),
    )

    warnings: list[str] = []
    for sec in sections:
        body, price_fixes = sanitize_prices(sec["body"], allowed)
        if price_fixes:
            warnings.append(
                f"В разделе «{sec['header']}» найдены и заменены выдуманные суммы: "
                + ", ".join(f"{f['old']}" for f in price_fixes)
            )
        sec["body"] = body

    if only_header:
        if not sections:
            raise AIResponseError(f"Модель не заполнила раздел «{only_header}». Повторите.")
        return GenResult(sections, rows, warnings)

    problems = _apply_deadline(sections, brief.deadline)
    for p in problems:
        warnings.append(f"Срок «{p['old']}» заменён на «{p['new']}».")
    _insert_price_block(sections, brief.budget, rows)
    return GenResult(sections, rows, warnings)