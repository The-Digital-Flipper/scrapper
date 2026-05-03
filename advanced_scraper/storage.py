from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


APP_DIR = Path.home() / ".advanced-scraper"
DB_PATH = APP_DIR / "scraper.db"
RUNS_DIR = APP_DIR / "runs"


def ensure_app_dirs() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    ensure_app_dirs()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        create table if not exists profiles (
            id integer primary key autoincrement,
            name text not null unique,
            config_json text not null,
            created_at real not null,
            updated_at real not null
        );

        create table if not exists runs (
            id integer primary key autoincrement,
            profile_id integer,
            status text not null,
            started_at real not null,
            finished_at real,
            command_json text not null,
            output_path text not null,
            event_log_path text not null,
            pages integer default 0,
            errors integer default 0,
            message text default '',
            foreign key(profile_id) references profiles(id)
        );

        create table if not exists result_index (
            id integer primary key autoincrement,
            run_id integer not null,
            url text not null,
            title text default '',
            status text default '',
            content_hash text default '',
            word_count integer default 0,
            record_json text default '',
            created_at real not null,
            foreign key(run_id) references runs(id)
        );
        """
    )
    columns = {row["name"] for row in conn.execute("pragma table_info(result_index)")}
    if "record_json" not in columns:
        conn.execute("alter table result_index add column record_json text default ''")
    conn.commit()


def save_profile(name: str, config: dict[str, Any]) -> int:
    now = time.time()
    with connect() as conn:
        existing = conn.execute("select id from profiles where name = ?", (name,)).fetchone()
        if existing:
            conn.execute(
                "update profiles set config_json = ?, updated_at = ? where id = ?",
                (json.dumps(config, sort_keys=True), now, existing["id"]),
            )
            return int(existing["id"])
        cur = conn.execute(
            "insert into profiles(name, config_json, created_at, updated_at) values(?, ?, ?, ?)",
            (name, json.dumps(config, sort_keys=True), now, now),
        )
        return int(cur.lastrowid)


def list_profiles() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("select * from profiles order by updated_at desc").fetchall()
    return [{**dict(row), "config": json.loads(row["config_json"])} for row in rows]


def get_profile(profile_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("select * from profiles where id = ?", (profile_id,)).fetchone()
    if not row:
        return None
    data = dict(row)
    data["config"] = json.loads(data["config_json"])
    return data


def create_run(profile_id: int | None, command: dict[str, Any], output_path: Path, event_log_path: Path) -> int:
    now = time.time()
    with connect() as conn:
        cur = conn.execute(
            """
            insert into runs(profile_id, status, started_at, command_json, output_path, event_log_path)
            values(?, 'running', ?, ?, ?, ?)
            """,
            (profile_id, now, json.dumps(command, sort_keys=True), str(output_path), str(event_log_path)),
        )
        return int(cur.lastrowid)


def finish_run(run_id: int, status: str, message: str = "") -> None:
    pages = 0
    errors = 0
    with connect() as conn:
        run = conn.execute("select output_path, event_log_path from runs where id = ?", (run_id,)).fetchone()
        if run:
            output = Path(run["output_path"])
            if output.exists() and output.suffix == ".jsonl":
                pages = sum(1 for _ in output.open("r", encoding="utf-8"))
            events = Path(run["event_log_path"])
            if events.exists():
                errors = sum(1 for line in events.open("r", encoding="utf-8") if "error" in line)
        conn.execute(
            "update runs set status = ?, finished_at = ?, pages = ?, errors = ?, message = ? where id = ?",
            (status, time.time(), pages, errors, message, run_id),
        )


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            select runs.*, profiles.name as profile_name
            from runs left join profiles on profiles.id = runs.profile_id
            order by runs.started_at desc limit ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_run(run_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            """
            select runs.*, profiles.name as profile_name
            from runs left join profiles on profiles.id = runs.profile_id
            where runs.id = ?
            """,
            (run_id,),
        ).fetchone()
    return dict(row) if row else None


def save_result_index(run_id: int, records: list[dict[str, Any]]) -> None:
    with connect() as conn:
        conn.execute("delete from result_index where run_id = ?", (run_id,))
        for record in records:
            conn.execute(
                """
                insert into result_index(run_id, url, title, status, content_hash, word_count, record_json, created_at)
                values(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    str(record.get("url") or ""),
                    str(record.get("title") or ""),
                    str(record.get("status") or ""),
                    str(record.get("content_hash") or ""),
                    int(record.get("word_count") or 0),
                    json.dumps(record, ensure_ascii=False, sort_keys=True),
                    time.time(),
                ),
            )


def list_result_index(run_id: int, limit: int = 100) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "select * from result_index where run_id = ? order by id desc limit ?",
            (run_id, limit),
        ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        data = dict(row)
        record_json = data.get("record_json") or ""
        if record_json:
            try:
                record = json.loads(record_json)
                if isinstance(record, dict):
                    data["record"] = record
            except json.JSONDecodeError:
                pass
        items.append(data)
    return items
