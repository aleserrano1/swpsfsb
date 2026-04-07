import sqlite3
import threading
from contextlib import contextmanager

_local = threading.local()
_db_path: str = ""


def set_path(path: str) -> None:
    global _db_path
    _db_path = path
    # Reset any cached connection for this thread
    if hasattr(_local, "conn"):
        try:
            _local.conn.close()
        except Exception:
            pass
        del _local.conn


def get_path() -> str:
    return _db_path


def _get_conn() -> sqlite3.Connection:
    if not _db_path:
        raise RuntimeError("Database path not set. Call set_path() first.")
    if not hasattr(_local, "conn") or _local.conn is None:
        conn = sqlite3.connect(_db_path, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return _local.conn


@contextmanager
def transaction():
    """Context manager that provides a cursor and commits on exit."""
    conn = _get_conn()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Execute a SELECT and return all rows."""
    conn = _get_conn()
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return rows


def query_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    """Execute a SELECT and return one row."""
    conn = _get_conn()
    cur = conn.execute(sql, params)
    row = cur.fetchone()
    cur.close()
    return row
