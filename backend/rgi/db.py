from contextlib import contextmanager
from .config import settings


def jsonb(value):
    from psycopg.types.json import Jsonb

    return Jsonb(value)


@contextmanager
def connect():
    import psycopg
    from psycopg.rows import dict_row

    # Short lived transactions; never hold a connection through model calls.
    with psycopg.connect(settings().database_url, row_factory=dict_row, connect_timeout=5) as conn:
        yield conn


def one(sql, params=()):
    with connect() as conn:
        return conn.execute(sql, params).fetchone()


def many(sql, params=()):
    with connect() as conn:
        return conn.execute(sql, params).fetchall()


@contextmanager
def checkpoints():
    """Checkpoint connection disables prepared statements explicitly.

    The pinned saver convenience constructor uses prepare_threshold=0 (always
    prepare), so construct the supported connection directly for pooler clarity.
    """
    import psycopg
    from psycopg.rows import dict_row
    from langgraph.checkpoint.postgres import PostgresSaver

    with psycopg.connect(
        settings().database_url,
        autocommit=True,
        prepare_threshold=None,
        row_factory=dict_row,
        connect_timeout=5,
    ) as conn:
        yield PostgresSaver(conn)
