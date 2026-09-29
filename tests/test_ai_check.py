"""Тесты живой проверки подключения к ИИ (src/ai/check.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config
from src.ai import check
from src.ai.errors import AIAuthError


class FakeOkProvider:
    name = "FakeGPT"
    model = "fake-model"

    def complete(self, system_prompt, user_prompt, timeout=None, temperature=0.4):
        return "привет"


class FakeErrorProvider(FakeOkProvider):
    def complete(self, system_prompt, user_prompt, timeout=None, temperature=0.4):
        raise AIAuthError(
            "Ошибка авторизации YandexGPT (HTTP 403).",
            detail="HTTP 403: PermissionDenied",
        )


def test_not_configured(monkeypatch):
    monkeypatch.setattr(config, "provider_configured", lambda *a, **kw: False)
    result = check.check_ai_connection()
    assert result["ok"] is False
    assert result["error_type"] == "NotConfigured"
    assert result["error_message"]


def test_ok(monkeypatch):
    monkeypatch.setattr(config, "provider_configured", lambda *a, **kw: True)
    monkeypatch.setattr(check, "create_provider", lambda *a, **kw: FakeOkProvider())
    result = check.check_ai_connection()
    assert result["ok"] is True
    assert result["answer"].strip() == "привет"
    assert result["provider"] == "FakeGPT"
    assert result["error_type"] == ""


def test_error(monkeypatch):
    monkeypatch.setattr(config, "provider_configured", lambda *a, **kw: True)
    monkeypatch.setattr(check, "create_provider", lambda *a, **kw: FakeErrorProvider())
    result = check.check_ai_connection()
    assert result["ok"] is False
    assert result["error_type"] == "AIAuthError"
    assert "403" in result["error_message"]
    assert "PermissionDenied" in result["error_detail"]


def test_hints_have_both_providers():
    yandex = check.connection_hints("yandex")
    gigachat = check.connection_hints("gigachat")
    assert "ai.languageModels.user" in yandex
    assert "base64" in gigachat
    assert "подсказок пока нет" in check.connection_hints("unknown")