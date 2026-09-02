"""DB connection. Prefer Postgres; fall back to SQLite if Postgres is down."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Tuple

ROOT = Path(__file__).resolve().parents[2]
SQLITE_PATH = ROOT / "data" / "finoptima.db"

Backend = str  # "postgres" | "sqlite"


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def database_url() -> str:
    _load_dotenv()
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://finoptima:finoptima@127.0.0.1:5432/finoptima",
    )


def openai_api_key() -> str:
    _load_dotenv()
    return os.environ.get("OPENAI_API_KEY", "").strip()


def groq_api_key() -> str:
    _load_dotenv()
    return os.environ.get("GROQ_API_KEY", "").strip()


def google_api_key() -> str:
    _load_dotenv()
    return (
        os.environ.get("GOOGLE_API_KEY", "").strip()
        or os.environ.get("GEMINI_API_KEY", "").strip()
    )


def enable_langsmith() -> None:
    """Turn on LangSmith tracing if a key is in .env. Graph nodes stay the same."""
    _load_dotenv()
    ls = os.environ.get("LANGSMITH_API_KEY", "").strip()
    lc = os.environ.get("LANGCHAIN_API_KEY", "").strip()
    if ls and not lc:
        os.environ["LANGCHAIN_API_KEY"] = ls
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", "finoptima")


def _sql(sql: str, backend: Backend) -> str:
    if backend == "sqlite":
        return sql.replace("%s", "?")
    return sql


def try_postgres():
    import psycopg
    from psycopg.rows import dict_row

    conn = psycopg.connect(database_url(), row_factory=dict_row, connect_timeout=2)
    conn.execute("SELECT 1")
    return conn


def sqlite_connect() -> sqlite3.Connection:
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _force_sqlite() -> bool:
    return os.environ.get("FINOPTIMA_FORCE_SQLITE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def postgres_has_money(conn: Any) -> bool:
    """True if Postgres already has seeded cloud rows."""
    try:
        row = conn.execute("SELECT COUNT(*) AS n FROM cloud_line_items").fetchone()
        return row is not None and int(row["n"]) > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def open_db() -> Tuple[Backend, Any]:
    """Postgres if it answers (seed if empty); else SQLite."""
    if _force_sqlite():
        return "sqlite", sqlite_connect()
    try:
        conn = try_postgres()
        if not postgres_has_money(conn):
            from db.build_db import apply_postgres_schema_and_fill

            apply_postgres_schema_and_fill(conn)
        return "postgres", conn
    except Exception:
        return "sqlite", sqlite_connect()


def probe_money_db() -> Backend:
    """Which store the engine would use. Does not seed."""
    if _force_sqlite():
        return "sqlite"
    try:
        conn = try_postgres()
        conn.close()
        return "postgres"
    except Exception:
        return "sqlite"


def fetchall(conn: Any, backend: Backend, sql: str, params: Iterable = ()) -> list:
    q = _sql(sql, backend)
    if backend == "postgres":
        return list(conn.execute(q, tuple(params)).fetchall())
    return list(conn.execute(q, tuple(params)).fetchall())
