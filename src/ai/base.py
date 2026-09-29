"""Абстракция LLM-провайдера и фабрика по имени из конфигурации."""
from __future__ import annotations

from abc import ABC, abstractmethod

from src import config
from src.ai.errors import AIConfigError


class LLMProvider(ABC):
    """Интерфейс провайдера. complete() возвращает текст ответа модели."""

    name: str = "LLM"
    model: str = ""

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout: float | None = None,
        temperature: float = 0.4,
    ) -> str:
        ...


def create_provider(provider_name: str | None = None) -> LLMProvider:
    """Создаёт провайдера по конфигурации. Пустые ключи -> AIConfigError."""
    name = (provider_name or config.AI_PROVIDER).lower()

    if name == "gigachat":
        if not config.GIGACHAT_API_KEY:
            raise AIConfigError(
                "Не задан GIGACHAT_API_KEY. Укажите его в .env (см. .env.example)."
            )
        from src.ai.gigachat import GigachatProvider

        return GigachatProvider()

    if name == "yandex":
        if not config.YANDEX_API_KEY or not config.YANDEX_FOLDER_ID:
            raise AIConfigError(
                "Для YandexGPT задайте YANDEX_API_KEY и YANDEX_FOLDER_ID в .env "
                "(см. .env.example)."
            )
        from src.ai.yandex import YandexProvider

        return YandexProvider()

    raise AIConfigError(
        f"Неизвестный AI_PROVIDER='{name}'. Допустимые значения: gigachat, yandex."
    )