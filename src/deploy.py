"""Файлы для развёртывания — русскоязычная замена англоязычного меню «Deploy».

Встроенная кнопка «Deploy» Streamlit (правый верхний угол) скрыта настройкой
``client.toolbarMode="viewer"`` в ``.streamlit/config.toml``: её меню зашито
в код Streamlit и не переводится. Здесь то же самое, но с русскими названиями:
скачать requirements.txt, Dockerfile, packages.txt и пример .streamlit/secrets.toml.

Правило безопасности: шаблон ``secrets.toml`` содержит ТОЛЬКО плейсхолдеры,
реальные значения из ``.env`` в код не попадают.
"""
from __future__ import annotations

from pathlib import Path

from src import config

BASE_DIR = config.BASE_DIR

#: Фиксированный набор файлов: имя -> функция, возвращающая содержимое.
#: Никаких произвольных путей — только эти «белые» имена.
DEPLOY_FILES: dict[str, callable] = {
    "requirements.txt": None,  # заполняется ниже
    "Dockerfile": None,
    "packages.txt": None,
    ".streamlit/secrets.toml": None,
}

_DOCKERFILE = """\
# ---------- Пример Dockerfile для развёртывания приложения ----------
# Сборка образа:
#   docker build -t ai-kp .
# Запуск контейнера:
#   docker run -p 8501:8501 ai-kp
#
# Версию Python при необходимости поменяйте на ту же, что на сервере/в облаке.
FROM python:3.9-slim

WORKDIR /app

# Сначала зависимости — слой кэшируется, пересборка проходит быстрее.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Затем весь проект. Файлы .env, data/, .git можно исключить через .dockerignore.
COPY . .

# Порт Streamlit по умолчанию.
EXPOSE 8501

# Проверка живости контейнера.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \\
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3).status == 200 else 1)"

# Запуск приложения.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
"""

_PACKAGES_TXT = """\
# Системные (apt) пакеты для разных платформ развёртывания — Streamlit Cloud и др.
# Раскомментируйте нужные строки, например:
#
# libpq-dev
# libxml2-dev
# libxslt1-dev
"""

_SECRETS_TEMPLATE = """\
# ============================================================
# Пример файла .streamlit/secrets.toml для развёртывания.
# Значения скопируйте из своего локального .env.
# ВАЖНО: не коммитьте этот файл в репозиторий — сюда попадают
# реальные ключи доступа!
# ============================================================

# Провайдер: yandex или gigachat
AI_PROVIDER = "yandex"

# --- YandexGPT ---
YANDEX_API_KEY = "AQVN-вставьте-свой-ключ"
YANDEX_FOLDER_ID = "b1g-вставьте-свой-каталог"

# --- GigaChat (если используете провайдер gigachat) ---
# GIGACHAT_API_KEY = "вставьте-base64-ключ"

# --- Прочее (необязательно) ---
# AI_TIMEOUT = 60
"""


def requirements_text() -> str:
    """Текущий requirements.txt проекта (реальный, обслуживаемый вручную)."""
    return (BASE_DIR / "requirements.txt").read_text(encoding="utf-8")


def dockerfile_text() -> str:
    return _DOCKERFILE


def packages_text() -> str:
    return _PACKAGES_TXT


def secrets_template() -> str:
    return _SECRETS_TEMPLATE


DEPLOY_FILES = {
    "requirements.txt": requirements_text,
    "Dockerfile": dockerfile_text,
    "packages.txt": packages_text,
    ".streamlit/secrets.toml": secrets_template,
}


def file_exists(name: str) -> bool:
    """Есть ли файл в проекте (с безопасной проверкой имени)."""
    if name not in DEPLOY_FILES:
        raise ValueError(f"Неизвестный файл развёртывания: {name!r}")
    return (BASE_DIR / name).exists()