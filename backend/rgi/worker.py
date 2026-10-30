"""One laptop worker. Heartbeats are independent from slow parsing/model calls."""

import argparse
import logging
import threading
import time
from uuid import uuid4
from .db import connect, one
from .jobs import claim, heartbeat, fence, LostLease, Cancelled, event, check_cancel, CheckpointBusy
from .ingest import ingest
from .research import execute
from .provider import QuotaPause, AmbiguousCall, BudgetExceeded, ConfigurationPause
from .config import settings

log = logging.getLogger("rgi.worker")


def process(job, owner):
    try:
        if job["kind"] == "ingest":
            ingest(job, owner)
        else:
            execute(one("SELECT * FROM runs WHERE id=?", (job["target_id"],)), job, owner)
        if job["kind"] == "research":
            check_cancel(job["target_id"])
        with connect() as conn:
            fence(conn, job["id"], owner)
            conn.execute(
                "UPDATE jobs SET status='complete',lease_until=NULL,updated_at=now() WHERE id=?",
                (job["id"],),
            )
            if job["kind"] == "research":
                conn.execute(
                    "UPDATE runs SET status='complete',updated_at=now() WHERE id=?", (job["target_id"],)
                )
    except LostLease:
        log.warning("Job lease lost; stale owner stopped")
    except Exception as exc:
        if isinstance(exc, CheckpointBusy):
            status, message = "queued", str(exc)
        elif isinstance(exc, QuotaPause):
            status, message = "waiting_for_quota", str(exc)
        elif isinstance(exc, Cancelled):
            status, message = "cancelled", str(exc)
        elif isinstance(exc, (AmbiguousCall, BudgetExceeded, ConfigurationPause)):
            status, message = "paused", str(exc)
        elif isinstance(exc, (ValueError, ImportError)):
            status = "failed"
            message = (
                str(exc)[:500]
                if isinstance(exc, ValueError)
                else "Required worker dependency missing; install worker extra"
            )
        else:
            status = "queued" if job["attempts"] < settings().max_attempts else "failed"
            message = (
                f"{type(exc).__name__}: processing failed; inspect local setup (sensitive details omitted)"
            )
        try:
            with connect() as conn:
                fence(conn, job["id"], owner)
                conn.execute(
                    """UPDATE jobs SET status=?,error=?,owner=NULL,lease_until=NULL,
                    available_at=after_seconds(?),updated_at=now() WHERE id=?""",
                    (status, message, min(60, 2 ** job["attempts"]), job["id"]),
                )
                if isinstance(exc, CheckpointBusy):
                    conn.execute("UPDATE jobs SET attempts=max(0,attempts-1) WHERE id=?", (job["id"],))
                if isinstance(exc, QuotaPause):
                    conn.execute("UPDATE jobs SET available_at=? WHERE id=?", (exc.retry_at, job["id"]))
                table = "runs" if job["kind"] == "research" else "document_versions"
                conn.execute(
                    f"UPDATE {table} SET status=?,error=? WHERE id=?", (status, message, job["target_id"])
                )
                if job["kind"] == "research":
                    event(conn, job["target_id"], "worker", status, {"message": message})
        except LostLease:
            log.warning("Failure arrived after ownership changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Claim at most one job, then exit")
    args = parser.parse_args()
    if settings().read_only:
        raise SystemExit("Read-only API mode: run worker only in an explicitly private owner environment")
    logging.basicConfig(level=logging.INFO)
    owner = f"laptop-{uuid4()}"
    current = {"job_id": None}
    stop = threading.Event()

    def pulse():
        while not stop.is_set():
            try:
                heartbeat(owner, current["job_id"])
            except Exception:
                log.warning("Worker heartbeat could not reach database")
            stop.wait(10)

    thread = threading.Thread(target=pulse, daemon=True)
    thread.start()
    try:
        while True:
            heartbeat(owner)
            job = claim(owner)
            if job:
                current["job_id"] = job["id"]
                process(job, owner)
                current["job_id"] = None
            if args.once:
                break
            if not job:
                time.sleep(2)
    finally:
        stop.set()
        thread.join(timeout=5)
        with connect() as conn:
            conn.execute("DELETE FROM workers WHERE id=?", (owner,))


if __name__ == "__main__":
    main()
