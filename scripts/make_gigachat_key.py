#!/usr/bin/env python3
"""Сборка GIGACHAT_API_KEY из Client ID и Client Secret.

Ключ GigaChat = base64("{client_id}:{client_secret}").
Скрипт собирает эту строку и (опционально) записывает её в .env.

Примеры:
    python scripts/make_gigachat_key.py                          # спросит ID и Secret
    python scripts/make_gigachat_key.py <client_id> <client_secret>
    python scripts/make_gigachat_key.py <client_id> <client_secret> --write-env
    python scripts/make_gigachat_key.py <id> <secret> --env-file .env

Полученный ключ чувствителен: никуда его не логируйте и не коммитьте
(.env уже в .gitignore).
"""
from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def make_key(client_id: str, client_secret: str) -> str:
    client_id = client_id.strip()
    client_secret = client_secret.strip()
    if not client_id:
        raise ValueError("Client ID пуст")
    if not client_secret:
        raise ValueError("Client Secret пуст")
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def write_env(env_path: Path, key: str) -> None:
    """Вставляет/обновляет GIGACHAT_API_KEY в .env, создавая файл при необходимости."""
    if not env_path.exists():
        example = PROJECT_ROOT / ".env.example"
        if example.exists():
            env_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            env_path.touch()

    lines = env_path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    replaced = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("GIGACHAT_API_KEY="):
            out.append(f"GIGACHAT_API_KEY={key}")
            replaced = True
        else:
            out.append(line)

    if not replaced:
        out.append(f"GIGACHAT_API_KEY={key}")

    # AI_PROVIDER должен указывать на gigachat для работы ключа.
    has_provider = any(l.lstrip().startswith("AI_PROVIDER=") for l in out)
    if not has_provider:
        out.append("AI_PROVIDER=gigachat")

    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("client_id", nargs="?", default="", help="Client ID из кабинета GigaChat")
    parser.add_argument("client_secret", nargs="?", default="", help="Client Secret из кабинета GigaChat")
    parser.add_argument(
        "--write-env",
        action="store_true",
        help="Записать ключ в .env (файл создаётся, если его нет)",
    )
    parser.add_argument(
        "--env-file",
        default=str(PROJECT_ROOT / ".env"),
        help="Путь к .env при использовании --write-env (по умолчанию проект/.env)",
    )
    args = parser.parse_args()

    client_id = args.client_id
    client_secret = args.client_secret
    if not client_id:
        client_id = input("Client ID: ").strip()
    if not client_secret:
        client_secret = input("Client Secret: ").strip()

    try:
        key = make_key(client_id, client_secret)
    except ValueError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1

    print("GIGACHAT_API_KEY  собран:")
    print(key)

    if args.write_env:
        env_path = Path(args.env_file)
        write_env(env_path, key)
        print(f"\nЗаписан в {env_path}. Можно запускать: streamlit run app.py")
    else:
        print(
            "\nСкопируйте его в .env в строку GIGACHAT_API_KEY="
            "\n(или выполните скрипт с флагом --write-env)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())