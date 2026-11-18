"""Read-only access to the SQLite database built by `scripts/load_ssa_alj.py`.

The server never writes to the database and never makes outbound network requests, so a
malformed tool argument can at worst produce a (parameterised) read query.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from ssa_alj_mcp.config import settings


class DatabaseUnavailable(RuntimeError):
    """The SQLite file is missing or unreadable."""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = settings.ssa_alj_db_path
    if not path.exists():
        raise DatabaseUnavailable(f"database file not found: {path}")
    try:
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    except sqlite3.Error as exc:  # pragma: no cover - defensive
        raise DatabaseUnavailable(f"cannot open database: {exc}") from exc
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    try:
        yield conn
    finally:
        conn.close()


def query(sql: str, params: tuple[Any, ...] | list[Any] = ()) -> list[dict[str, Any]]:
    """Run a parameterised read query and return rows as plain dicts."""
    with connect() as conn:
        return [dict(row) for row in conn.execute(sql, params)]


def query_one(sql: str, params: tuple[Any, ...] | list[Any] = ()) -> dict[str, Any] | None:
    rows = query(sql, params)
    return rows[0] if rows else None
