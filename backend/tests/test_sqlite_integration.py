"""Actual file-backed SQLite integration; no external database or hidden fallback."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from pathlib import Path
import pytest

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def database(isolated_settings):
    from rgi.db import initialize

    initialize()
    return isolated_settings.database_path


def collection():
    from rgi.db import connect

    with connect() as conn:
        return conn.execute(
            "INSERT INTO collections(id,name) VALUES (?,'Integration synthetic fixture') RETURNING id",
            (uuid4(),),
        ).fetchone()["id"]


def ingest_document(cid, title="Control", data=None):
    from rgi.ingest import upload
    from rgi.jobs import claim
    from rgi.worker import process
    from rgi.db import one

    doc = upload(cid, title, data or (ROOT / "fixtures/paper-a.pdf").read_bytes())
    # Dispatch specifically this document in an isolated test database.
    owner = f"test-{uuid4()}"
    job = claim(owner)
    assert job and job["target_id"] == doc["id"], "Use a dedicated empty test database"
    process(job, owner)
    assert one("SELECT status FROM document_versions WHERE id=?", (doc["id"],))["status"] == "ready"
    return doc


def test_duplicate_versions_scoped_retrieval_and_provenance(database):
    from rgi.ingest import upload
    from rgi.retrieval import search, context

    cid, other = collection(), collection()
    first = ingest_document(cid)
    assert upload(cid, "Control", (ROOT / "fixtures/paper-a.pdf").read_bytes())["duplicate"]
    second = ingest_document(cid, data=(ROOT / "fixtures/paper-b.pdf").read_bytes())
    assert first["id"] != second["id"]
    assert search(other, "memory retrieval") == []
    hits = search(cid, "memory retrieval", versions=[str(first["id"])])
    assert hits and all(h["version_id"] == first["id"] for h in hits)
    assert hits[0]["keyword_rank"] and hits[0]["vector_rank"]
    assert context(cid, hits[0]["id"])["passage"]["page"] == 1
    with pytest.raises(ValueError, match="outside"):
        context(other, hits[0]["id"])


def test_atomic_race_expired_lease_and_fencing(database):
    from rgi.jobs import enqueue, claim, fence, LostLease
    from rgi.db import connect

    with connect() as conn:
        enqueue(conn, "ingest", uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        claimed = list(pool.map(claim, ["worker-a", "worker-b"]))
    jobs = [job for job in claimed if job]
    assert len(jobs) == 1
    job = jobs[0]
    with connect() as conn:
        conn.execute("UPDATE jobs SET lease_until=after_seconds(-1) WHERE id=?", (job["id"],))
    recovered = claim("replacement")
    assert recovered["id"] == job["id"]
    with connect() as conn:
        with pytest.raises(LostLease):
            fence(conn, job["id"], job["owner"])
        conn.execute("UPDATE jobs SET status='complete' WHERE id=?", (job["id"],))


def test_persisted_fixture_graph_report_and_checkpoint(database):
    from rgi.api import create_run, cancel
    from rgi.schemas import RunInput
    from rgi.jobs import claim
    from rgi.worker import process
    from rgi.db import one
    from rgi.db import checkpoints
    from rgi.research import build_graph, Investigation

    cid = collection()
    ingest_document(cid)
    run = create_run(
        RunInput(
            provider="fixture",
            collection_id=cid,
            question="How was memory retrieval studied in the toy setting?",
        )
    )
    job = claim("graph-worker")
    process(job, "graph-worker")
    saved = one("SELECT * FROM runs WHERE id=?", (run["id"],))
    assert saved["status"] == "complete", saved["error"]
    assert "SYNTHETIC FIXTURE" in saved["report"]
    assert saved["result"]["reviews"][0]["disposition"] == "contradicted"
    with checkpoints() as saver:
        graph = build_graph(Investigation(saved, job, "graph-worker"), saver)
        snapshot = graph.get_state({"configurable": {"thread_id": str(run["id"])}})
        assert snapshot.values and not snapshot.next
    queued = create_run(
        RunInput(provider="fixture", collection_id=cid, question="Cancel this queued fixture investigation?")
    )
    cancel(queued["id"])
    assert one("SELECT status FROM runs WHERE id=?", (queued["id"],))["status"] == "cancelled"


def test_quota_pause_resume_and_no_paid_fallback(database, monkeypatch):
    from datetime import datetime, timezone
    from rgi.api import create_run, resume
    from rgi.schemas import RunInput, ResumeInput
    from rgi.jobs import claim
    from rgi.worker import process
    from rgi.provider import Fixture, QuotaPause
    from rgi.db import one

    cid = collection()
    ingest_document(cid)
    run = create_run(
        RunInput(
            provider="fixture", collection_id=cid, question="Quota pause fixture control on memory retrieval?"
        )
    )
    original = Fixture.generate
    calls = []

    def throttled(self, *args):
        calls.append("fixture")
        raise QuotaPause(retry_at=datetime.now(timezone.utc))

    monkeypatch.setattr(Fixture, "generate", throttled)
    process(claim("quota-worker"), "quota-worker")
    assert one("SELECT status FROM runs WHERE id=?", (run["id"],))["status"] == "waiting_for_quota"
    assert calls == ["fixture"]
    assert claim("another-worker") is None
    monkeypatch.setattr(Fixture, "generate", original)
    resume(run["id"], ResumeInput())
    process(claim("quota-worker"), "quota-worker")
    assert one("SELECT status,provider FROM runs WHERE id=?", (run["id"],)) == {
        "status": "complete",
        "provider": "fixture",
    }


def test_restart_resumes_completed_sqlite_nodes(database, monkeypatch):
    from rgi.api import create_run
    from rgi.schemas import RunInput
    from rgi.jobs import claim
    from rgi.worker import process
    from rgi.research import Investigation
    from rgi.db import one, connect

    cid = collection()
    ingest_document(cid)
    run = create_run(
        RunInput(
            provider="fixture",
            collection_id=cid,
            question="Worker restart fixture for memory retrieval reliability?",
        )
    )
    original = Investigation.role
    crashed = []

    def interrupt_before_review(self, role, state):
        if role == "review" and not crashed:
            crashed.append(True)
            raise RuntimeError("Simulated worker restart before reviewer")
        return original(self, role, state)

    monkeypatch.setattr(Investigation, "role", interrupt_before_review)
    process(claim("first-process"), "first-process")
    calls_before = one("SELECT calls FROM runs WHERE id=?", (run["id"],))["calls"]
    assert calls_before == 4
    with connect() as conn:
        conn.execute("UPDATE jobs SET available_at=now() WHERE target_id=?", (run["id"],))
    process(claim("replacement-process"), "replacement-process")
    saved = one("SELECT status,calls FROM runs WHERE id=?", (run["id"],))
    assert saved == {"status": "complete", "calls": 6}


def test_ambiguous_call_requires_explicit_acknowledgement(database):
    from fastapi import HTTPException
    from rgi.api import create_run, resume
    from rgi.schemas import RunInput, ResumeInput
    from rgi.db import connect, one

    cid = collection()
    ingest_document(cid)
    run = create_run(
        RunInput(
            provider="fixture",
            collection_id=cid,
            question="Uncertain external call fixture control on memory?",
        )
    )
    with connect() as conn:
        conn.execute("UPDATE runs SET status='paused',reserved_tokens=123 WHERE id=?", (run["id"],))
        conn.execute("UPDATE jobs SET status='paused' WHERE target_id=?", (run["id"],))
        conn.execute(
            "INSERT INTO llm_calls(cache_key,run_id,role,status) VALUES (?,?,'plan','pending')",
            (str(uuid4()), run["id"]),
        )
    with pytest.raises(HTTPException) as exc:
        resume(run["id"], ResumeInput())
    assert exc.value.status_code == 409
    resume(run["id"], ResumeInput(acknowledge_duplicate_call=True))
    assert one("SELECT tokens,reserved_tokens,usage_unknown FROM runs WHERE id=?", (run["id"],)) == {
        "tokens": 123,
        "reserved_tokens": 0,
        "usage_unknown": True,
    }
    # Don't leave a queued research job for other isolated tests.
    from rgi.api import cancel

    cancel(run["id"])


def test_file_lock_serializes_lease_replacement(database):
    from rgi.api import create_run
    from rgi.schemas import RunInput
    from rgi.jobs import claim
    from rgi.worker import process
    from rgi.db import connect, run_lock, one

    cid = collection()
    ingest_document(cid)
    run = create_run(
        RunInput(
            provider="fixture",
            collection_id=cid,
            question="Checkpoint session race fixture for memory retrieval?",
        )
    )
    with run_lock(run["id"]):
        process(claim("replacement-session"), "replacement-session")
        saved = one("SELECT status,calls FROM runs WHERE id=?", (run["id"],))
        assert saved == {"status": "queued", "calls": 0}
        assert one("SELECT attempts FROM jobs WHERE target_id=?", (run["id"],))["attempts"] == 0
    # Closing the file releases its OS lock, including after process death.
    with connect() as conn:
        conn.execute("UPDATE jobs SET available_at=now() WHERE target_id=?", (run["id"],))
    process(claim("replacement-session"), "replacement-session")
    assert one("SELECT status FROM runs WHERE id=?", (run["id"],))["status"] == "complete"


def test_schema_idempotent_fts_syntax_and_health(database):
    from rgi.db import initialize, one
    from rgi.api import health
    from rgi.jobs import heartbeat
    from rgi.retrieval import search

    initialize()
    cid = collection()
    ingest_document(cid)
    heartbeat("healthy-worker")
    assert health()["database_engine"] == "sqlite"
    assert health()["worker"]["online"] is True
    assert health()["primary_provider"] == "groq"
    assert one("SELECT count(*) AS n FROM passages")["n"] > 0
    # Literal terms never become FTS operators or SQL.
    assert isinstance(search(cid, 'memory OR "retrieval" -- * AND (NOT)'), list)


def test_process_lock_contention_and_death_release(database):
    import subprocess
    import sys
    from rgi.db import run_lock
    from rgi.jobs import CheckpointBusy

    run_id = str(uuid4())
    code = "from rgi.db import run_lock; import sys; ctx=run_lock(sys.argv[1]); ctx.__enter__(); print('locked',flush=True); sys.stdin.read()"
    child = subprocess.Popen(
        [sys.executable, "-c", code, run_id], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    try:
        assert child.stdout.readline().strip() == "locked"
        with pytest.raises(CheckpointBusy):
            with run_lock(run_id):
                pass
    finally:
        child.kill()
        child.wait(timeout=10)
    with run_lock(run_id):
        pass


def test_uncertain_model_response_pauses_without_repeating(database, monkeypatch):
    from rgi.api import create_run, resume
    from rgi.schemas import RunInput, ResumeInput
    from rgi.jobs import claim
    from rgi.worker import process
    from rgi.provider import Fixture
    from rgi.db import one
    from fastapi import HTTPException

    cid = collection()
    ingest_document(cid)
    run = create_run(RunInput(provider="fixture", collection_id=cid, question="Uncertain response control?"))
    calls = []

    def failed(*args):
        calls.append(True)
        raise TimeoutError("Synthetic unknown provider outcome")

    monkeypatch.setattr(Fixture, "generate", failed)
    process(claim("uncertain-worker"), "uncertain-worker")
    assert one("SELECT status FROM runs WHERE id=?", (run["id"],))["status"] == "paused"
    assert claim("replacement") is None
    assert len(calls) == 1
    with pytest.raises(HTTPException) as raised:
        resume(run["id"], ResumeInput())
    assert raised.value.status_code == 409


def test_database_survives_fresh_process(database):
    import subprocess
    import sys

    cid = collection()
    code = "from rgi.db import one; import sys; print(one('SELECT name FROM collections WHERE id=?',(sys.argv[1],))['name'])"
    result = subprocess.run(
        [sys.executable, "-c", code, str(cid)], capture_output=True, text=True, check=True, timeout=10
    )
    assert result.stdout.strip() == "Integration synthetic fixture"


def test_consistent_backup_contains_committed_rows_and_checkpoints(database, tmp_path):
    import sqlite3
    import subprocess
    import sys

    cid = collection()
    backup = tmp_path / "backup.sqlite3"
    subprocess.run(
        [sys.executable, "scripts/backup_db.py", str(backup)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    with sqlite3.connect(backup) as conn:
        assert conn.execute("SELECT id FROM collections WHERE id=?", (cid,)).fetchone()[0] == cid
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT name FROM sqlite_master WHERE name='checkpoints'").fetchone()
