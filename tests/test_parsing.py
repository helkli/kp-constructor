"""Тесты парсинга ответа модели, обработки ошибок API и фабрики провайдеров."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from src.ai.errors import (
    AIAuthError,
    AIHttpError,
    AIRateLimitError,
    AIResponseError,
    friendly_message,
    map_http_status,
)
from src.ai.guard import parse_sections

EXPECTED = [
    "Обращение",
    "Понимание задачи",
    "Предлагаемые услуги",
    "Сроки",
    "Условия и порядок работы",
    "Следующие шаги",
]


SAMPLE = """## Обращение
Здравствуйте, коллеги!
## Понимание задачи
Нужна поддержка серверов.
## Предлагаемые услуги
Опишем состав работ.
## Сроки
Выполним за 2 недели.
## Условия и порядок работы
Работаем по регламенту.
## Следующие шаги
Обсудим детали.
"""


def test_parse_full_response():
    sections = parse_sections(SAMPLE, EXPECTED)
    assert [s["header"] for s in sections] == EXPECTED
    assert "Здравствуйте" in sections[0]["body"]


def test_parse_with_numbered_headers():
    numbered = "1) Обращение\nПривет\n2) Сроки\nЧерез месяц\n"
    sections = parse_sections(numbered, ["Обращение", "Сроки"])
    assert sections[0]["header"] == "Обращение"
    assert sections[1]["header"] == "Сроки"


def test_parse_skips_code_fences():
    raw = "```\n" + SAMPLE + "\n```"
    sections = parse_sections(raw, EXPECTED)
    assert len(sections) == len(EXPECTED)


def test_parse_missing_section_raises():
    raw = SAMPLE.replace("## Следующие шаги\nОбсудим детали.\n", "")
    with pytest.raises(AIResponseError):
        parse_sections(raw, EXPECTED, require_all=True)


def test_parse_unknown_section_raises():
    raw = SAMPLE + "## Заключение\nЧто-то ещё\n"
    with pytest.raises(AIResponseError):
        parse_sections(raw, EXPECTED, require_all=True)


def test_parse_single_section_not_require_all():
    raw = "## Сроки\nЧерез неделю.\n"
    sections = parse_sections(raw, ["Сроки"], require_all=False)
    assert sections[0]["header"] == "Сроки"


def test_empty_response_raises():
    with pytest.raises(AIResponseError):
        parse_sections("", EXPECTED)


# ---------- обработка ошибок API ----------
def test_map_http_401_to_auth_error():
    err = map_http_status(401, "GigaChat", "unauthorized body")
    assert isinstance(err, AIAuthError)


def test_map_http_429_to_rate_limit():
    err = map_http_status(429, "GigaChat", "")
    assert isinstance(err, AIRateLimitError)


def test_map_http_500_to_http_error():
    err = map_http_status(500, "GigaChat", "boom")
    assert isinstance(err, AIHttpError)
    assert err.status == 500


def test_friendly_message_never_leaks_detail():
    err = map_http_status(500, "GigaChat", "secret-token-in-response 123")
    msg = friendly_message(err)
    assert "secret-token" not in msg


def test_friendly_message_config_error():
    from src.ai.errors import AIConfigError

    msg = friendly_message(AIConfigError("Не задан ключ."))
    assert ".env" in msg