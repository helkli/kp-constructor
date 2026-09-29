"""Клиент GigaChat API (Сбер).

Поток: OAuth-токен -> chat/completions. Ключ — только из окружения (config).
Ошибки превращаются в типизированные исключения src/ai/errors.py.
Таймаут по умолчанию — 60 с (config.AI_TIMEOUT).
"""
from __future__ import annotations

import time
import uuid

import requests

from src import config
from src.ai.base import LLMProvider
from src.ai.errors import (
    AIResponseError,
    map_http_status,
    map_requests_exception,
)


class GigachatProvider(LLMProvider):
    name = "GigaChat"
    model = config.GIGACHAT_MODEL

    def __init__(self) -> None:
        self._token: str | None = None
        self._token_expires_at: float = 0.0  # unix time

    # ---------- OAuth ----------
    def _get_token(self, timeout: float) -> str:
        # Кэш токена с запасом 60 секунд.
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        headers = {
            "Authorization": f"Basic {config.GIGACHAT_API_KEY}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        try:
            resp = requests.post(
                config.GIGACHAT_OAUTH_URL,
                headers=headers,
                data={"scope": "GIGACHAT_API_PERS"},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise map_requests_exception(exc, self.name) from exc

        if resp.status_code != 200:
            raise map_http_status(resp.status_code, self.name, resp.text[:500])

        try:
            data = resp.json()
            token = str(data["access_token"])
            expires_ms = int(data.get("expires_at", 0))
        except (KeyError, ValueError, TypeError) as exc:
            raise AIResponseError(
                f"{self.name}: неожиданный ответ при получении токена.",
                detail=str(exc),
            ) from exc

        # expires_at приходит в миллисекундах Unix-времени.
        ttl_sec = max(60.0, (expires_ms - time.time() * 1000) / 1000.0)
        self._token = token
        self._token_expires_at = time.time() + ttl_sec
        return token

    # ---------- Запрос ----------
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout: float | None = None,
        temperature: float = 0.4,
    ) -> str:
        timeout = timeout or config.AI_TIMEOUT
        token = self._get_token(timeout)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config.GIGACHAT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": 4096,
        }

        try:
            resp = requests.post(
                f"{config.GIGACHAT_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise map_requests_exception(exc, self.name) from exc

        # Токен мог протухнуть — один повторный заход за токеном и один ретрай.
        if resp.status_code == 401 and self._token:
            self._token = None
            token = self._get_token(timeout)
            headers["Authorization"] = f"Bearer {token}"
            try:
                resp = requests.post(
                    f"{config.GIGACHAT_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
            except requests.RequestException as exc:
                raise map_requests_exception(exc, self.name) from exc

        if resp.status_code != 200:
            raise map_http_status(resp.status_code, self.name, resp.text[:500])

        try:
            data = resp.json()
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIResponseError(
                "Не удалось прочитать текст из ответа GigaChat.",
                detail=str(exc),
            ) from exc