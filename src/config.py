"""Конфигурация приложения.

Ключи API читаются ТОЛЬКО из переменных окружения или .env (python-dotenv).
Захардкоженных ключей в коде быть не должно.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# --- ИИ-провайдер ---
AI_PROVIDER = os.getenv("AI_PROVIDER", "gigachat").strip().lower()

# --- GigaChat ---
GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY", "").strip()
GIGACHAT_BASE_URL = os.getenv(
    "GIGACHAT_BASE_URL", "https://gigachat.devices.sberbank.ru/api/v1"
).rstrip("/")
GIGACHAT_OAUTH_URL = os.getenv(
    "GIGACHAT_OAUTH_URL", "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
)
GIGACHAT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat:latest")

# --- YandexGPT ---
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "").strip()
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "").strip()
YANDEX_MODEL = os.getenv("YANDEX_MODEL", "yandexgpt-lite")

# --- Прочее ---
AI_TIMEOUT = float(os.getenv("AI_TIMEOUT", "60"))  # сек, по ТЗ максимум 60

PROVIDERS = {"gigachat", "yandex"}


def provider_configured(provider: str | None = None) -> bool:
    """Проверяет, что у выбранного провайдера заполнены учётные данные."""
    p = (provider or AI_PROVIDER).lower()
    if p not in PROVIDERS:
        return False
    if p == "gigachat":
        return bool(GIGACHAT_API_KEY)
    if p == "yandex":
        return bool(YANDEX_API_KEY and YANDEX_FOLDER_ID)
    return False