"""Клиент YandexGPT (Yandex AI Studio / Foundation Models v1).

Ключ — только из окружения (config). Ошибки — типизированные (src/ai/errors.py).
"""
from __future__ import annotations

import requests

from src import config
from src.ai.base import LLMProvider
from src.ai.errors import (
    AIResponseError,
    map_http_status,
    map_requests_exception,
)

YANDEX_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


class YandexProvider(LLMProvider):
    name = "YandexGPT"
    model = config.YANDEX_MODEL

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout: float | None = None,
        temperature: float = 0.4,
    ) -> str:
        timeout = timeout or config.AI_TIMEOUT
        headers = {
            "Authorization": f"Api-Key {config.YANDEX_API_KEY}",
            "x-folder-id": config.YANDEX_FOLDER_ID,
            "Content-Type": "application/json",
        }
        payload = {
            "modelUri": f"gpt://{config.YANDEX_FOLDER_ID}/{config.YANDEX_MODEL}",
            "completionOptions": {
                "stream": False,
                "temperature": temperature,
                "maxTokens": 2000,
            },
            "messages": [
                {"role": "system", "text": system_prompt},
                {"role": "user", "text": user_prompt},
            ],
        }

        try:
            resp = requests.post(
                YANDEX_API_URL, headers=headers, json=payload, timeout=timeout
            )
        except requests.RequestException as exc:
            raise map_requests_exception(exc, self.name) from exc

        if resp.status_code != 200:
            raise map_http_status(resp.status_code, self.name, resp.text[:500])

        try:
            data = resp.json()
            alternatives = data["result"]["alternatives"]
            return str(alternatives[0]["message"]["text"]).strip()
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIResponseError(
                "Не удалось прочитать текст из ответа YandexGPT.",
                detail=str(exc),
            ) from exc