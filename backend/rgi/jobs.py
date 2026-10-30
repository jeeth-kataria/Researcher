"""SQLite queue: BEGIN IMMEDIATE claims, renewable leases and fenced writes."""

from uuid import uuid4
from .db import connect, one, json_value
from .config import settings


class LostLease(RuntimeError):
    pass


class Cancelled(RuntimeError):
    pass


class CheckpointBusy(RuntimeError):
    pass


def enqueue(conn, kind, target):
    conn.execute(
        "INSERT INTO jobs(id,kind,target_id) VALUES (?,?,?) ON CONFLICT DO NOTHING",
        (uuid4(), kind, target),
    )


def claim(owner):
    with connect() as conn:
        # Failed last attempts are made terminal instead of leaving immortal jobs.
        exhausted = conn.execute(
            """UPDATE jobs SET status='failed', error='Retry limit exhausted'
            WHERE attempts >= ? AND (status='queued' OR (status='running' AND lease_until < now()))
            RETURNING kind,target_id""",
            (settings().max_attempts,),
        ).fetchall()
        for job in exhausted:
            table = "runs" if job["kind"] == "research" else "document_versions"
            conn.execute(
                f"UPDATE {table} SET status='failed',error='Retry limit exhausted' WHERE id=?",
                (job["target_id"],),
            )
        return conn.execute(
            """UPDATE jobs SET status='running',owner=?,
            lease_until=after_seconds(?), attempts=attempts+1,updated_at=now()
            WHERE id=(SELECT id FROM jobs WHERE attempts < ? AND available_at <= now()
              AND (status='queued' OR (status='running' AND lease_until < now()))
              ORDER BY created_at,id LIMIT 1) RETURNING *""",
            (owner, settings().lease_seconds, settings().max_attempts),
        ).fetchone()


def heartbeat(owner, job_id=None):
    with connect() as conn:
        conn.execute(
            "INSERT INTO workers(id) VALUES (?) ON CONFLICT(id) DO UPDATE SET heartbeat_at=now()", (owner,)
        )
        if job_id:
            conn.execute(
                """UPDATE jobs SET lease_until=after_seconds(?),updated_at=now()
                WHERE id=? AND owner=? AND status='running' AND lease_until>now()""",
                (settings().lease_seconds, job_id, owner),
            )


def fence(conn, job_id, owner):
    row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row or row["owner"] != owner or row["status"] != "running":
        raise LostLease("Job ownership changed")
    alive = conn.execute("SELECT lease_until > now() AS alive FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not alive["alive"]:
        raise LostLease("Lease expired")


def check_cancel(run_id):
    run = one("SELECT cancel_requested FROM runs WHERE id=?", (run_id,))
    if run and run["cancel_requested"]:
        raise Cancelled("Cancelled between steps; an in-flight provider call may have completed")


def event(conn, run_id, node, kind, data, duration_ms=None):
    conn.execute(
        "INSERT INTO events(run_id,node,kind,data,duration_ms) VALUES (?,?,?,?,?)",
        (run_id, node, kind, json_value(data), duration_ms),
    )
