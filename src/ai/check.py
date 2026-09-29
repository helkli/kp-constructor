"""Живая проверка подключения к ИИ-провайдеру (кнопка в UI и скрипт test_ai.py).

Никакие ключи и персональные данные в результат и логи не попадают.
"""
from __future__ import annotations

from src import config
from src.ai.base import create_provider
from src.ai.errors import AIError, friendly_message


def check_ai_connection(timeout: float | None = None) -> dict:
    """Делает короткий тестовый запрос к настроенному провайдеру.

    Возвращает словарь с ключами:
      ok, provider, model, answer, error_type, error_message, error_detail.
    """
    if not config.provider_configured():
        return {
            "ok": False,
            "provider": config.AI_PROVIDER,
            "model": "",
            "answer": "",
            "error_type": "NotConfigured",
            "error_message": (
                "Ключи не заполнены. Добавьте GIGACHAT_API_KEY или YANDEX_API_KEY "
                "и YANDEX_FOLDER_ID в .env (см. .env.example и README.md)."
            ),
            "error_detail": "",
        }

    provider = create_provider(config.AI_PROVIDER)
    try:
        answer = provider.complete(
            "Ты — ассистент. Отвечай одним словом.",
            "Напиши слово привет",
            timeout=timeout or min(config.AI_TIMEOUT, 30),
        )
    except AIError as exc:
        return {
            "ok": False,
            "provider": provider.name,
            "model": provider.model,
            "answer": "",
            "error_type": type(exc).__name__,
            "error_message": friendly_message(exc),
            "error_detail": exc.detail,
        }
    return {
        "ok": True,
        "provider": provider.name,
        "model": provider.model,
        "answer": answer.strip()[:140],
        "error_type": "",
        "error_message": "",
        "error_detail": "",
    }


def connection_hints(provider: str) -> str:
    """Подсказки по устранению типовых неполадок для конкретного провайдера."""
    if provider == "yandex":
        return (
            "Для YandexGPT проверьте в консоли console.yandex.cloud:\n"
            "1. Каталог в .env (YANDEX_FOLDER_ID) — тот же, на который выданы права.\n"
            "2. Сервисному аккаунту (его ключ в YANDEX_API_KEY) выдана роль "
            "ai.languageModels.user на этот каталог (Каталог > Права доступа).\n"
            "3. Доступ к моделям в каталоге включён (YandexGPT) и платёжный аккаунт активен.\n"
            "4. Ключ не отозван и не истёк — при сомнении пересоздайте API-ключ."
        )
    if provider == "gigachat":
        return (
            "Для GigaChat проверьте:\n"
            "1. GIGACHAT_API_KEY — корректный base64 от client_id:client_secret "
            "(см. scripts/make_gigachat_key.py).\n"
            "2. Доступ к GigaChat API активирован в developers.sberbank.ru."
        )
    return f"Для провайдера «{provider}» подсказок пока нет."