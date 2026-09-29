"""Типизированные ошибки ИИ-провайдеров и человеко-понятные сообщения.

Обработка ошибок API:
- каждый сценарий сбоя превращается в конкретный класс ошибки;
- наружу (в UI) отдаётся только friendly_message() — понятный текст на русском,
  без служебной информации и без следов ключей.
"""
from __future__ import annotations


class AIError(Exception):
    """Базовая ошибка ИИ-слоя."""

    def __init__(self, message: str, *, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.detail = detail


class AIConfigError(AIError):
    """Нет/неправильно настроен провайдер (ключи, имя провайдера)."""


class AIAuthError(AIError):
    """Ошибка авторизации: 401/403, неверный или истёкший ключ."""


class AIRateLimitError(AIError):
    """Превышены лимиты провайдера: HTTP 429."""


class AITimeoutError(AIError):
    """Провайдер не ответил за отведённое время."""


class AINetworkError(AIError):
    """Проблема соединения с сервером провайдера."""


class AIHttpError(AIError):
    """Прочие HTTP-ошибки провайдера."""

    def __init__(self, status: int, provider: str, detail: str = ""):
        self.status = status
        self.provider = provider
        super().__init__(
            f"Ошибка {provider} (HTTP {status}).",
            detail=detail,
        )


class AIResponseError(AIError):
    """Ответ модели не удалось разобрать (пустой, битый, не все разделы)."""


def map_http_status(status: int, provider: str, detail: str = "") -> AIError:
    """Преобразует HTTP-статус провайдера в типизированную ошибку."""
    if status in (401, 403):
        return AIAuthError(
            f"Ошибка авторизации {provider} (HTTP {status}).",
            detail=f"HTTP {status}: {detail[:500]}",
        )
    if status == 429:
        return AIRateLimitError(
            f"Превышен лимит запросов к {provider}. Попробуйте через минуту.",
            detail=f"HTTP 429: {detail[:500]}",
        )
    return AIHttpError(status, provider, detail)


def map_requests_exception(exc: BaseException, provider: str) -> AIError:
    """Преобразует исключения requests.session в типизированные ошибки."""
    # Импортируем лениво: requests может отсутствовать только в тестах на низком слое.
    import requests

    if isinstance(exc, requests.Timeout):
        return AITimeoutError(
            f"ИИ-сервис {provider} не ответил за отведённое время. Попробуйте ещё раз."
        )
    if isinstance(exc, requests.ConnectionError):
        return AINetworkError(
            f"Нет соединения с {provider}. Проверьте интернет и попробуйте снова."
        )
    return AINetworkError(
        f"Сетевая ошибка при обращении к {provider}: {exc}. Попробуйте позже."
    )


def friendly_message(exc: Exception) -> str:
    """Человеко-понятное сообщение для UI, без ключей и технических деталей."""
    if isinstance(exc, AIConfigError):
        return (
            "Не настроен ИИ-провайдер. Скопируйте .env.example в .env и укажите "
            "ключ (GIGACHAT_API_KEY или YANDEX_API_KEY). Подробности — в README.md."
        )
    if isinstance(exc, AIAuthError):
        return exc.message
    if isinstance(exc, AIRateLimitError):
        return exc.message
    if isinstance(exc, AITimeoutError):
        return exc.message
    if isinstance(exc, AINetworkError):
        return exc.message
    if isinstance(exc, AIHttpError):
        return f"Ошибка {exc.provider} (HTTP {exc.status}). Попробуйте позже."
    if isinstance(exc, AIResponseError):
        return exc.message
    return "Неожиданная ошибка при генерации. Попробуйте ещё раз."