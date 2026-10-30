"""Real pgvector tests. Requires a dedicated disposable RGI_TEST_DATABASE_URL.

No SQLite fallback. This file skips honestly when the database is unavailable.
"""

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from pathlib import Path
import pytest

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def database():
    url = os.getenv("RGI_TEST_DATABASE_URL")
    if not url:
        pytest.skip("RGI_TEST_DATABASE_URL not supplied; real PostgreSQL tests not run")
    pytest.importorskip("psycopg")
    from rgi.config import settings

    original = {k: os.environ.get(k) for k in ("RGI_DATABASE_URL", "RGI_EMBEDDER", "RGI_PARSER")}
    os.environ.update(RGI_DATABASE_URL=url, RGI_EMBEDDER="fixture", RGI_PARSER="pypdf")
    settings.cache_clear()
    subprocess.run(["alembic", "upgrade", "head"], cwd=ROOT, check=True)
    from langgraph.checkpoint.postgres import PostgresSaver

    with PostgresSaver.from_conn_string(url) as saver:
        saver.setup()
    yield
    for k, value in original.items():
        if value is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = value
    settings.cache_clear()


def collection():
    from rgi.db import connect

    with connect() as conn:
        return conn.execute(
            "INSERT INTO collections(id,name) VALUES (%s,'Integration synthetic fixture') RETURNING id",
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
    assert one("SELECT status FROM document_versions WHERE id=%s", (doc["id"],))["status"] == "ready"
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
        conn.execute("UPDATE jobs SET lease_until=now()-interval '1 second' WHERE id=%s", (job["id"],))
    recovered = claim("replacement")
    assert recovered["id"] == job["id"]
    with connect() as conn:
        with pytest.raises(LostLease):
            fence(conn, job["id"], job["owner"])
        conn.execute("UPDATE jobs SET status='complete' WHERE id=%s", (job["id"],))


def test_persisted_fixture_graph_report_and_checkpoint(database):
    from rgi.api import create_run, cancel
    from rgi.schemas import RunInput
    from rgi.jobs import claim
    from rgi.worker import process
    from rgi.db import one
    from langgraph.checkpoint.postgres import PostgresSaver
    from rgi.research import build_graph, Investigation
    from rgi.config import settings

    cid = collection()
    ingest_document(cid)
    run = create_run(
        RunInput(collection_id=cid, question="How was memory retrieval studied in the toy setting?")
    )
    job = claim("graph-worker")
    process(job, "graph-worker")
    saved = one("SELECT * FROM runs WHERE id=%s", (run["id"],))
    assert saved["status"] == "complete", saved["error"]
    assert "SYNTHETIC FIXTURE" in saved["report"]
    assert saved["result"]["reviews"][0]["disposition"] == "contradicted"
    with PostgresSaver.from_conn_string(settings().database_url) as saver:
        graph = build_graph(Investigation(saved, job, "graph-worker"), saver)
        snapshot = graph.get_state({"configurable": {"thread_id": str(run["id"])}})
        assert snapshot.values and not snapshot.next
    queued = create_run(RunInput(collection_id=cid, question="Cancel this queued fixture investigation?"))
    cancel(queued["id"])
    assert one("SELECT status FROM runs WHERE id=%s", (queued["id"],))["status"] == "cancelled"


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
    run = create_run(RunInput(collection_id=cid, question="Quota pause fixture control on memory retrieval?"))
    original = Fixture.generate
    calls = []

    def throttled(self, *args):
        calls.append("fixture")
        raise QuotaPause(retry_at=datetime.now(timezone.utc))

    monkeypatch.setattr(Fixture, "generate", throttled)
    process(claim("quota-worker"), "quota-worker")
    assert one("SELECT status FROM runs WHERE id=%s", (run["id"],))["status"] == "waiting_for_quota"
    assert calls == ["fixture"]
    assert claim("another-worker") is None
    monkeypatch.setattr(Fixture, "generate", original)
    resume(run["id"], ResumeInput())
    process(claim("quota-worker"), "quota-worker")
    assert one("SELECT status,provider FROM runs WHERE id=%s", (run["id"],)) == {
        "status": "complete",
        "provider": "fixture",
    }


def test_restart_resumes_completed_postgres_nodes(database, monkeypatch):
    from rgi.api import create_run
    from rgi.schemas import RunInput
    from rgi.jobs import claim
    from rgi.worker import process
    from rgi.research import Investigation
    from rgi.db import one, connect

    cid = collection()
    ingest_document(cid)
    run = create_run(
        RunInput(collection_id=cid, question="Worker restart fixture for memory retrieval reliability?")
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
    calls_before = one("SELECT calls FROM runs WHERE id=%s", (run["id"],))["calls"]
    assert calls_before == 4
    with connect() as conn:
        conn.execute("UPDATE jobs SET available_at=now() WHERE target_id=%s", (run["id"],))
    process(claim("replacement-process"), "replacement-process")
    saved = one("SELECT status,calls FROM runs WHERE id=%s", (run["id"],))
    assert saved == {"status": "complete", "calls": 6}


def test_ambiguous_call_requires_explicit_acknowledgement(database):
    from fastapi import HTTPException
    from rgi.api import create_run, resume
    from rgi.schemas import RunInput, ResumeInput
    from rgi.db import connect, one

    cid = collection()
    ingest_document(cid)
    run = create_run(
        RunInput(collection_id=cid, question="Uncertain external call fixture control on memory?")
    )
    with connect() as conn:
        conn.execute("UPDATE runs SET status='paused',reserved_tokens=123 WHERE id=%s", (run["id"],))
        conn.execute("UPDATE jobs SET status='paused' WHERE target_id=%s", (run["id"],))
        conn.execute(
            "INSERT INTO llm_calls(cache_key,run_id,role,status) VALUES (%s,%s,'plan','pending')",
            (str(uuid4()), run["id"]),
        )
    with pytest.raises(HTTPException) as exc:
        resume(run["id"], ResumeInput())
    assert exc.value.status_code == 409
    resume(run["id"], ResumeInput(acknowledge_duplicate_call=True))
    assert one("SELECT tokens,reserved_tokens,usage_unknown FROM runs WHERE id=%s", (run["id"],)) == {
        "tokens": 123,
        "reserved_tokens": 0,
        "usage_unknown": True,
    }
    # Don't leave a queued research job for other isolated tests.
    from rgi.api import cancel

    cancel(run["id"])


def test_checkpoint_session_serializes_lease_replacement(database):
    from rgi.api import create_run
    from rgi.schemas import RunInput
    from rgi.jobs import claim
    from rgi.worker import process
    from rgi.db import connect, checkpoints, one

    cid = collection()
    ingest_document(cid)
    run = create_run(
        RunInput(collection_id=cid, question="Checkpoint session race fixture for memory retrieval?")
    )
    with checkpoints() as prior_session:
        prior_session.conn.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", (str(run["id"]),))
        process(claim("replacement-session"), "replacement-session")
        saved = one("SELECT status,calls FROM runs WHERE id=%s", (run["id"],))
        assert saved == {"status": "queued", "calls": 0}
        assert one("SELECT attempts FROM jobs WHERE target_id=%s", (run["id"],))["attempts"] == 0
    # Closing the prior DB session releases its lock, including after process death.
    with connect() as conn:
        conn.execute("UPDATE jobs SET available_at=now() WHERE target_id=%s", (run["id"],))
    process(claim("replacement-session"), "replacement-session")
    assert one("SELECT status FROM runs WHERE id=%s", (run["id"],))["status"] == "complete"
