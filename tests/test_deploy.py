"""Тесты модуля развёртывания src/deploy.py (русская замена меню «Deploy»).

Ключевая проверка — безопасность: пример .streamlit/secrets.toml не должен
содержать реальных значений ключей из .env.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from src import config, deploy  # noqa: E402

EXPECTED_FILES = {
    "requirements.txt",
    "Dockerfile",
    "packages.txt",
    ".streamlit/secrets.toml",
}


def test_deploy_files_set_is_exact():
    """Набор файлов фиксированный — ни больше, ни меньше."""
    assert set(deploy.DEPLOY_FILES) == EXPECTED_FILES


def test_every_factory_returns_non_empty_text():
    for name, factory in deploy.DEPLOY_FILES.items():
        text = factory()
        assert isinstance(text, str) and text.strip(), f"{name}: пустое содержимое"


@pytest.mark.parametrize(
    "env_name",
    ["AI_PROVIDER", "YANDEX_API_KEY", "YANDEX_FOLDER_ID", "GIGACHAT_API_KEY"],
)
def test_secrets_template_contains_expected_env_names(env_name):
    """В шаблоне указаны все переменные окружения, которые читает приложение."""
    assert env_name in deploy.secrets_template()


@pytest.mark.parametrize(
    "real_key",
    [
        config.GIGACHAT_API_KEY,
        config.YANDEX_API_KEY,
        config.YANDEX_FOLDER_ID,
    ],
)
def test_secrets_template_has_no_real_keys(real_key):
    """Guard: реальные значения ключей из .env не должны попадать в шаблон."""
    if not real_key or len(real_key) < 8:
        pytest.skip("ключ не настроен в окружении")
    assert real_key not in deploy.secrets_template()


def test_dockerfile_has_run_and_healthcheck():
    text = deploy.dockerfile_text()
    assert text.startswith("#")  # начинается с комментария
    assert "FROM python:" in text
    assert 'streamlit", "run", "app.py' in text
    assert "HEALTHCHECK" in text
    assert "EXPOSE 8501" in text


def test_packages_has_apt_hint():
    text = deploy.packages_text()
    assert "apt" in text
    assert text.lstrip().startswith("#")


def test_requirements_text_reads_real_project_file():
    text = deploy.requirements_text()
    assert "streamlit" in text.lower()
    # совпадает с файлом на диске
    disk = (config.BASE_DIR / "requirements.txt").read_text(encoding="utf-8")
    assert text == disk


@pytest.mark.parametrize("name", sorted(EXPECTED_FILES))
def test_file_exists_returns_bool(name):
    """file_exists для известных имён возвращает bool и не падает."""
    result = deploy.file_exists(name)
    assert isinstance(result, bool)


def test_file_exists_unknown_name_raises():
    with pytest.raises(ValueError):
        deploy.file_exists("../../etc/passwd")
    with pytest.raises(ValueError):
        deploy.file_exists("secret.txt")