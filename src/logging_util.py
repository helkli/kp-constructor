"""Логирование вызовов ИИ: промпт и ответ — без персональных данных.

Промпт и ответ обезличиваются функцией depersonalize (guard.py) ДО передачи сюда.
Ретеншн логов — 30 дней (чистится при инициализации хранилища).
"""
from __future__ import annotations


def log_ai_call(
    storage,
    provider: str,
    model: str,
    prompt: str,
    response: str,
    duration_ms: int | None = None,
    error: str | None = None,
) -> None:
    """Записывает вызов ИИ в таблицу ai_logs (промпт уже обезличен)."""
    try:
        storage.add_log(
            provider=provider,
            model=model,
            prompt=prompt,
            response=response,
            duration_ms=duration_ms,
            error=error,
        )
    except Exception:
        # Логирование не должно ронять генерацию.
        pass