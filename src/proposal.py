"""КП: модель данных черновика и история версий."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Section:
    header: str = ""
    body: str = ""


@dataclass
class Proposal:
    id: int | None = None
    brief_id: int | None = None
    version: int = 1
    status: str = "draft"  # draft | final
    sections: list[Section] = field(default_factory=list)
    pricing: list[dict] = field(default_factory=list)
    created_at: str = ""
    # Ревизия содержания: растёт при перегенерации разделов/всего текста.
    # Используется в ключах виджетов редактора, чтобы Streamlit показывал
    # новый текст, а не устаревшее значение виджета.
    revision: int = 0

    @staticmethod
    def sections_to_json(sections: list[Section | dict]) -> str:
        items = []
        for s in sections:
            if isinstance(s, Section):
                items.append({"header": s.header, "body": s.body})
            else:
                items.append({"header": s.get("header", ""), "body": s.get("body", "")})
        return json.dumps(items, ensure_ascii=False)

    @staticmethod
    def sections_from_json(raw: str) -> list[dict]:
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
        return [
            {"header": s.get("header", ""), "body": s.get("body", "")}
            for s in data
            if isinstance(s, dict)
        ]

    @staticmethod
    def pricing_from_json(raw: str) -> list[dict]:
        """Список строк прайсовой таблицы ({name, price_text, ...}), как сохранено."""
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
        return [dict(s) for s in data if isinstance(s, dict)]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")