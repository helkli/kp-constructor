#!/usr/bin/env python3
"""Проверка живого подключения к настроенному ИИ-провайдеру.

Читает .env (AI_PROVIDER, ключи), делает короткий запрос к модели и печатает результат.
Ключи не выводятся. Использование:
    python scripts/test_ai.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ai.check import check_ai_connection, connection_hints  # noqa: E402


def main() -> int:
    result = check_ai_connection()

    print(f"AI_PROVIDER = {result['provider']}")

    if result["ok"]:
        print("OK: подключение работает")
        print(f"Ответ модели: {result['answer']}")
        print(f"Провайдер: {result['provider']}, модель: {result['model']}")
        return 0

    if result["error_type"] == "NotConfigured":
        print(result["error_message"])
        return 1

    print(f"Провайдер: {result['provider']}, модель: {result['model']}")
    print(f"ОШИБКА: {result['error_type']} — {result['error_message']}")
    if result["error_detail"]:
        print("Детали ответа API:", result["error_detail"][:300])
    print()
    print(connection_hints(result["provider"]))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())