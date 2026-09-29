"""Хранилище SQLite: БД создаётся автоматически, при пустой БД — сиды для прайса и шаблона."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from src.config import BASE_DIR
from src.proposal import now_iso
from src.template import DEFAULT_SECTIONS, default_template

DB_PATH = BASE_DIR / "data" / "app.db"

DEFAULT_SERVICES = [
    # (название, цена или None, единица, активна)
    ("ИТ-аудит и инвентаризация", 25000, "", 1),
    ("Администрирование серверов", 12000, "мес", 1),
    ("Мониторинг ИТ-инфраструктуры", 8000, "мес", 1),
    ("Резервное копирование и восстановление", 6000, "мес", 1),
    ("Обновление ПО и патчи безопасности", 5000, "мес", 1),
    ("Поддержка пользователей 1С", 9000, "мес", 1),
    ("Подключение и настройка рабочих мест", 3500, "рабочее место", 1),
    ("Настройка и сопровождение корпоративной почты", None, "мес", 1),
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS services (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL UNIQUE,
    price REAL,
    unit  TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS briefs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    client     TEXT NOT NULL,
    task       TEXT NOT NULL,
    deadline   TEXT NOT NULL,
    budget     TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brief_services (
    brief_id   INTEGER NOT NULL REFERENCES briefs(id) ON DELETE CASCADE,
    service_id INTEGER NOT NULL REFERENCES services(id),
    PRIMARY KEY (brief_id, service_id)
);

CREATE TABLE IF NOT EXISTS proposals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    brief_id      INTEGER NOT NULL REFERENCES briefs(id) ON DELETE CASCADE,
    version       INTEGER NOT NULL,
    status        TEXT NOT NULL DEFAULT 'draft',
    sections_json TEXT NOT NULL DEFAULT '[]',
    pricing_json  TEXT NOT NULL DEFAULT '[]',
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS templates (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    name          TEXT NOT NULL,
    sections_json TEXT NOT NULL,
    active        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ai_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    provider    TEXT NOT NULL,
    model       TEXT NOT NULL,
    prompt      TEXT NOT NULL,
    response    TEXT NOT NULL,
    duration_ms INTEGER,
    error       TEXT
);
"""


class Storage:
    """Обёртка над SQLite. Одно постоянное соединение, sqlite3.Row для чтения."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path or DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_db()
        self._seed()
        self.purge_logs(30)

    # ---------- база ----------
    def _init_db(self) -> None:
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def _seed(self) -> None:
        if self._conn.execute("SELECT COUNT(*) FROM services").fetchone()[0] == 0:
            self._conn.executemany(
                "INSERT INTO services (name, price, unit, active) VALUES (?, ?, ?, ?)",
                DEFAULT_SERVICES,
            )
            self._conn.commit()
        if self._conn.execute("SELECT COUNT(*) FROM templates").fetchone()[0] == 0:
            tmpl = default_template()
            self._conn.execute(
                "INSERT INTO templates (id, name, sections_json, active) VALUES (1, ?, ?, 1)",
                (tmpl["name"], json.dumps(tmpl["sections"], ensure_ascii=False)),
            )
            self._conn.commit()

    # ---------- услуги / прайс ----------
    def list_services(self, active_only: bool = False) -> list[dict]:
        sql = "SELECT * FROM services"
        if active_only:
            sql += " WHERE active = 1"
        sql += " ORDER BY id"
        rows = self._conn.execute(sql).fetchall()
        return [dict(r) for r in rows]

    def upsert_service(
        self,
        name: str,
        price,
        unit: str = "",
        active: bool = True,
        service_id: int | None = None,
    ) -> int:
        price_db = None if price in (None, "") else float(str(price).replace(",", "."))
        if service_id:
            self._conn.execute(
                "UPDATE services SET name = ?, price = ?, unit = ?, active = ? WHERE id = ?",
                (name.strip(), price_db, unit.strip(), int(active), service_id),
            )
            self._conn.commit()
            return service_id
        cur = self._conn.execute(
            "INSERT INTO services (name, price, unit, active) VALUES (?, ?, ?, ?)",
            (name.strip(), price_db, unit.strip(), int(active)),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def set_service_active(self, service_id: int, active: bool) -> None:
        # Мягкое удаление: старые КП остаются валидными (ТЗ FR-16).
        self._conn.execute(
            "UPDATE services SET active = ? WHERE id = ?", (int(active), service_id)
        )
        self._conn.commit()

    # ---------- шаблон ----------
    def get_active_template(self) -> dict:
        row = self._conn.execute(
            "SELECT * FROM templates WHERE id = 1 AND active = 1"
        ).fetchone()
        if row is None:
            # На случай, если активный шаблон выключили — отдаём дефолт.
            tmpl = default_template()
            return {"id": 1, "name": tmpl["name"], "sections": tmpl["sections"], "active": 1}
        sections = json.loads(row["sections_json"] or "[]")
        return {"id": row["id"], "name": row["name"], "sections": sections, "active": row["active"]}

    def save_template(self, name: str, sections: list[dict]) -> None:
        self._conn.execute(
            "UPDATE templates SET name = ?, sections_json = ? WHERE id = 1",
            (name.strip() or "Основной шаблон КП", json.dumps(sections, ensure_ascii=False)),
        )
        self._conn.commit()

    # ---------- бриф ----------
    def create_brief(self, client: str, task: str, deadline: str, budget: str, service_ids: list[int]) -> int:
        cur = self._conn.execute(
            "INSERT INTO briefs (client, task, deadline, budget, created_at) VALUES (?, ?, ?, ?, ?)",
            (client, task, deadline, budget or "", now_iso()),
        )
        brief_id = int(cur.lastrowid)
        self._conn.executemany(
            "INSERT INTO brief_services (brief_id, service_id) VALUES (?, ?)",
            [(brief_id, sid) for sid in service_ids],
        )
        self._conn.commit()
        return brief_id

    def get_brief(self, brief_id: int) -> dict:
        row = self._conn.execute(
            "SELECT * FROM briefs WHERE id = ?", (brief_id,)
        ).fetchone()
        if row is None:
            return {}
        data = dict(row)
        data["service_ids"] = [
            r["service_id"]
            for r in self._conn.execute(
                "SELECT service_id FROM brief_services WHERE brief_id = ? ORDER BY service_id",
                (brief_id,),
            ).fetchall()
        ]
        return data

    def list_briefs(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM briefs ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # ---------- КП ----------
    def next_version(self, brief_id: int) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 AS v FROM proposals WHERE brief_id = ?",
            (brief_id,),
        ).fetchone()
        return int(row["v"])

    def create_proposal(
        self,
        brief_id: int,
        version: int,
        status: str,
        sections: list[dict],
        pricing: list[dict],
    ) -> int:
        # Принимаем и словари, и объекты Section (dataclass из src.proposal).
        sections_json = json.dumps(
            [
                s
                if isinstance(s, dict)
                else {"header": getattr(s, "header", ""), "body": getattr(s, "body", "")}
                for s in sections
            ],
            ensure_ascii=False,
        )
        cur = self._conn.execute(
            "INSERT INTO proposals (brief_id, version, status, sections_json, pricing_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                brief_id,
                version,
                status,
                sections_json,
                json.dumps(pricing, ensure_ascii=False),
                now_iso(),
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def list_proposals(self) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT p.id, p.brief_id, p.version, p.status, p.sections_json, p.pricing_json,
                   p.created_at, b.client
            FROM proposals p JOIN briefs b ON b.id = p.brief_id
            ORDER BY p.created_at DESC, p.id DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def get_proposal(self, proposal_id: int) -> dict:
        row = self._conn.execute(
            """
            SELECT p.id, p.brief_id, p.version, p.status, p.sections_json, p.pricing_json,
                   p.created_at, b.client
            FROM proposals p JOIN briefs b ON b.id = p.brief_id
            WHERE p.id = ?
            """,
            (proposal_id,),
        ).fetchone()
        return dict(row) if row else {}

    def update_proposal_status(self, proposal_id: int, status: str) -> None:
        self._conn.execute(
            "UPDATE proposals SET status = ? WHERE id = ?", (status, proposal_id)
        )
        self._conn.commit()

    # ---------- логи ----------
    def add_log(
        self,
        provider: str,
        model: str,
        prompt: str,
        response: str,
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO ai_logs (ts, provider, model, prompt, response, duration_ms, error) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (now_iso(), provider, model, prompt, response, duration_ms, error),
        )
        self._conn.commit()

    def purge_logs(self, days: int = 30) -> None:
        """Ретеншн логов: удаляем записи старше N дней."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
        self._conn.execute("DELETE FROM ai_logs WHERE ts < ?", (cutoff,))
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass