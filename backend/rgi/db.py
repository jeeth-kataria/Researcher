"""Local SQLite persistence. WAL readers, short serialized writes, explicit initialization."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID
from .config import settings

SCHEMA_VERSION = 1
JSON_COLUMNS = {
    "warnings",
    "item_ids",
    "boxes",
    "embedding",
    "manifest",
    "config",
    "result",
    "data",
    "payload",
    "response",
}
BOOL_COLUMNS = {"cancel_requested", "usage_unknown", "alive", "online"}


def utc(value=None):
    return (
        (value or datetime.now(timezone.utc))
        .astimezone(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def json_value(value):
    return json.dumps(value, ensure_ascii=False, default=str, allow_nan=False)


def _row(cursor, values):
    row = dict(zip((c[0] for c in cursor.description), values))
    for key, value in row.items():
        if value is not None and key in JSON_COLUMNS:
            row[key] = json.loads(value)
        elif value is not None and key in BOOL_COLUMNS:
            row[key] = bool(value)
    return row


def _bind(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return utc(value)
    return value


class Connection:
    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql, params=()):
        return self.raw.execute(sql, tuple(_bind(p) for p in params))


def _open(*, create=False):
    path = settings().database_path.resolve()
    if not create and not path.is_file():
        raise RuntimeError("SQLite database not initialized; run python scripts/init_db.py")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15, isolation_level=None, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute("PRAGMA synchronous=FULL")
    conn.create_function("now", 0, utc)
    conn.create_function(
        "after_seconds", 1, lambda seconds: utc(datetime.now(timezone.utc) + timedelta(seconds=seconds))
    )
    return conn


@contextmanager
def connect(*, write=True):
    conn = _open()
    conn.row_factory = _row
    try:
        if write:
            # Serialize writes before count/check/claim reads. Transactions are
            # short; model calls and CPU parsing never hold the write lock.
            conn.execute("BEGIN IMMEDIATE")
        yield Connection(conn)
        if write:
            conn.commit()
    except BaseException:
        if write:
            conn.rollback()
        raise
    finally:
        conn.close()


def one(sql, params=()):
    with connect(write=False) as conn:
        return conn.execute(sql, params).fetchone()


def many(sql, params=()):
    with connect(write=False) as conn:
        return conn.execute(sql, params).fetchall()


@contextmanager
def checkpoints():
    from langgraph.checkpoint.sqlite import SqliteSaver

    conn = _open()
    try:
        yield SqliteSaver(conn)
    finally:
        conn.close()


@contextmanager
def run_lock(run_id):
    """OS lock covers graph invocation AND its post-node checkpoint writes.

    Local host only. Process death releases the lock; no database transaction
    stays open during a remote call. The supported local host is macOS/Linux.
    """
    import fcntl
    from .jobs import CheckpointBusy

    identity = str(UUID(str(run_id)))
    database = settings().database_path.resolve()
    directory = database.parent / (database.name + ".locks")
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / (identity + ".lock")).open("a+b") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise CheckpointBusy(
                "Prior checkpoint writer is finishing; retry dispatch without spending quota"
            ) from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def initialize():
    schema = Path(__file__).with_name("schema.sql").read_text()
    conn = _open(create=True)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, SCHEMA_VERSION):
            raise RuntimeError("Unsupported SQLite schema version; back up before upgrading")
        if version == 0:
            conn.executescript(
                "BEGIN IMMEDIATE;\n" + schema + f"\nPRAGMA user_version={SCHEMA_VERSION};\nCOMMIT;"
            )
    finally:
        conn.close()
    with checkpoints() as saver:
        saver.setup()
