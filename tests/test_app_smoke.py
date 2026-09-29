"""Smoke-тесты страниц Streamlit через AppTest: все экраны рендерятся без исключений.

Проверяет запуск app.py и каждой страницы (без кликов и вызовов ИИ).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402

from src.brief import Brief  # noqa: E402
from src.proposal import Proposal, Section  # noqa: E402

PS = AppTest


def _one_script(script):
    at = AppTest.from_file(script, default_timeout=15)
    at.run()
    if at.exception:
        raise AssertionError(
            f"Страница {script} упала: {at.exception[0].value}"
        )
    return at


def test_app_main_page():
    _one_script("app.py")


def test_brief_page():
    _one_script("pages/1_Бриф.py")


def test_draft_page_without_proposal():
    # Без КП в сессии страница показывает заглушку, но не падает.
    _one_script("pages/2_Черновик.py")


def test_draft_page_with_proposal():
    # Регрессия: рендер редактора разделов НЕ должен писать в session_state
    # под ключами уже созданных виджетов (Streamlit запрещает это).
    at = AppTest.from_file("pages/2_Черновик.py", default_timeout=15)
    at.session_state["brief"] = Brief(
        client="ООО Тест", task="Задача", service_ids=[1], deadline="2 недели", budget=""
    )
    at.session_state["proposal"] = Proposal(
        version=1,
        sections=[
            Section(header="Обращение", body="Здравствуйте!"),
            Section(header="Сроки", body="две недели"),
        ],
    )
    at.run()
    if at.exception:
        raise AssertionError(f"Черновик с КП упал: {at.exception[0].value}")


def test_preview_page_without_proposal():
    _one_script("pages/3_Предпросмотр.py")


def test_history_page_empty():
    _one_script("pages/4_История.py")


def test_settings_page_as_manager():
    # По умолчанию роль «Менеджер» — страница настройки блокируется, без падений.
    _one_script("pages/5_Настройки.py")


def test_settings_page_as_director():
    # Роль «Руководитель»: рендерятся прайс, шаблон и вкладка «Подключение к ИИ».
    at = AppTest.from_file("pages/5_Настройки.py", default_timeout=15)
    at.session_state["app_role"] = "Руководитель"
    at.run()
    if at.exception:
        raise AssertionError(f"Настройки (руководитель) упали: {at.exception[0].value}")