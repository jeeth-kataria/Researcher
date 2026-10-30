"""Thin local API; all parsing and research are dispatched as durable jobs."""

import hmac
from uuid import UUID, uuid4
from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, FileResponse
from .config import settings
from .db import connect, one, many, json_value
from .schemas import CollectionInput, RunInput, ResumeInput
from .jobs import enqueue
from .ingest import upload
from .retrieval import search, context, latest_manifest
from .storage import path_for

app = FastAPI(title="Research Gap Investigator", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(ValueError)
async def invalid(_request, exc):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=422, content={"detail": str(exc)})


def access(authorization: str = Header(default="")):
    token = settings().owner_token
    if token and not hmac.compare_digest(authorization, f"Bearer {token}"):
        raise HTTPException(401, "Owner authorization required")


def writable(_=Depends(access)):
    if settings().read_only:
        raise HTTPException(403, "Read-only example mode; uploads and research creation disabled")


@app.get("/api/health")
def health():
    try:
        one("SELECT 1")
        worker = one(
            "SELECT max(heartbeat_at) AS last,coalesce(max(heartbeat_at>after_seconds(-30)),false) AS online FROM workers"
        )
        return {
            "api": "online",
            "database": "online",
            "worker": worker,
            "read_only": settings().read_only,
            "parser": settings().parser,
            "embedder": settings().embedder,
            "database_engine": "sqlite",
            "primary_provider": "groq",
            "groq_configured": bool(settings().groq_api_key and settings().free_tier_ack),
            "gemini_configured": bool(settings().gemini_api_key and settings().free_tier_ack),
        }
    except Exception:
        # Health does not expose URLs, credentials or raw database exceptions.
        return {
            "api": "online",
            "database": "unavailable",
            "worker": {"online": False},
            "read_only": settings().read_only,
            "gemini_configured": False,
            "groq_configured": False,
        }


@app.get("/api/collections", dependencies=[Depends(access)])
def collections():
    return many("SELECT * FROM collections ORDER BY created_at DESC")


@app.post("/api/collections", dependencies=[Depends(writable)], status_code=201)
def create_collection(body: CollectionInput):
    with connect() as conn:
        return conn.execute(
            "INSERT INTO collections(id,name,scope) VALUES (?,?,?) RETURNING *",
            (uuid4(), body.name, body.scope),
        ).fetchone()


@app.get("/api/collections/{collection_id}/papers", dependencies=[Depends(access)])
def papers(collection_id: UUID):
    return many(
        """SELECT p.id AS paper_id,p.title,p.source_url,d.* FROM papers p
        JOIN document_versions d ON d.paper_id=p.id WHERE p.collection_id=?
        ORDER BY p.created_at,d.created_at DESC""",
        (collection_id,),
    )


@app.post("/api/collections/{collection_id}/papers", dependencies=[Depends(writable)], status_code=202)
async def upload_pdf(collection_id: UUID, title: str = Form(...), file: UploadFile = File(...)):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(415, "Expected application/pdf")
    data = await file.read(settings().max_upload_mb * 1024 * 1024 + 1)
    await file.close()
    # CPU work is absent here; parsing/embedding happens in worker.
    return upload(collection_id, title, data)


@app.get("/api/collections/{collection_id}/search", dependencies=[Depends(access)])
def inspect_search(collection_id: UUID, q: str, k: int = 8, diversity: int = 3):
    return search(collection_id, q, k, diversity)


@app.get("/api/collections/{collection_id}/evidence/{evidence_id}", dependencies=[Depends(access)])
def evidence(collection_id: UUID, evidence_id: UUID):
    return context(collection_id, evidence_id)


@app.get("/api/versions/{version_id}/pdf", dependencies=[Depends(access)])
def pdf(version_id: UUID):
    doc = one("SELECT storage_key FROM document_versions WHERE id=?", (version_id,))
    if not doc:
        raise HTTPException(404, "Document version not found")
    return FileResponse(
        path_for(doc["storage_key"]),
        media_type="application/pdf",
        headers={"Content-Security-Policy": "sandbox", "X-Content-Type-Options": "nosniff"},
    )


@app.post("/api/runs", dependencies=[Depends(writable)], status_code=202)
def create_run(body: RunInput):
    manifest = latest_manifest(body.collection_id)
    if not manifest:
        raise ValueError("Ingest at least one supported PDF before starting research")
    if body.provider != "fixture":
        key = settings().groq_api_key if body.provider == "groq" else settings().gemini_api_key
        if not key or not settings().free_tier_ack:
            raise ValueError("Configure key and explicitly acknowledge billing-disabled free tier in .env")
        if any(m["embedding_id"].startswith("fixture") for m in manifest):
            raise ValueError("Fixture embeddings cannot be used for real research; ingest using BGE")
    provenance = (
        "SYNTHETIC FIXTURE — not real research"
        if body.provider == "fixture"
        else f"{body.provider.title()} corpus-only research; requires human verification"
    )
    # Serialize UUIDs into an immutable JSON corpus manifest.
    manifest = [{k: str(v) for k, v in m.items()} for m in manifest]
    config = {
        "budget": body.budget.model_dump(),
        "prompt_version": "research-v1",
        "schema_version": "role-v1",
    }
    with connect() as conn:
        run = conn.execute(
            """INSERT INTO runs(id,collection_id,question,scope,mode,provider,model,
            provenance,manifest,config) VALUES (?,?,?,?,?,?,?,?,?,?) RETURNING *""",
            (
                uuid4(),
                body.collection_id,
                body.question,
                body.scope,
                body.mode,
                body.provider,
                settings().groq_model
                if body.provider == "groq"
                else settings().gemini_model
                if body.provider == "gemini"
                else "fixture-v1",
                provenance,
                json_value(manifest),
                json_value(config),
            ),
        ).fetchone()
        enqueue(conn, "research", run["id"])
        return run


@app.get("/api/runs", dependencies=[Depends(access)])
def runs():
    return many("""SELECT id,collection_id,question,scope,mode,provider,provenance,status,calls,tokens,
        usage_unknown,created_at,updated_at FROM runs ORDER BY created_at DESC LIMIT 100""")


@app.get("/api/runs/{run_id}", dependencies=[Depends(access)])
def run_detail(run_id: UUID):
    run = one("SELECT * FROM runs WHERE id=?", (run_id,))
    if not run:
        raise HTTPException(404, "Run not found")
    return {**run, "events": many("SELECT * FROM events WHERE run_id=? ORDER BY id", (run_id,))}


@app.post("/api/runs/{run_id}/cancel", dependencies=[Depends(writable)])
def cancel(run_id: UUID):
    with connect() as conn:
        row = conn.execute(
            """UPDATE runs SET cancel_requested=true,updated_at=now(),
            status=CASE WHEN status IN ('queued','waiting_for_quota','paused') THEN 'cancelled' ELSE status END
            WHERE id=? RETURNING *""",
            (run_id,),
        ).fetchone()
        conn.execute(
            "UPDATE jobs SET status='cancelled' WHERE target_id=? AND status IN ('queued','waiting_for_quota','paused')",
            (run_id,),
        )
        if not row:
            raise HTTPException(404, "Run not found")
        return row


@app.post("/api/runs/{run_id}/resume", dependencies=[Depends(writable)])
def resume(run_id: UUID, body: ResumeInput = Body(default=ResumeInput())):
    with connect() as conn:
        original = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not original:
            raise HTTPException(404, "Run not found")
        uncertain = conn.execute(
            "SELECT cache_key FROM llm_calls WHERE run_id=? AND status IN ('pending','uncertain')", (run_id,)
        ).fetchall()
        if uncertain and not body.acknowledge_duplicate_call:
            raise HTTPException(
                409, "Previous call outcome unknown; acknowledge_duplicate_call=true may consume quota twice"
            )
        if original["status"] not in ("paused", "waiting_for_quota") or original["cancel_requested"]:
            raise HTTPException(409, "Only quota/config-paused runs can resume")
        if body.budget:
            config = {**original["config"], "budget": body.budget.model_dump()}
            conn.execute("UPDATE runs SET config=? WHERE id=?", (json_value(config), run_id))
        if uncertain:
            # Unknown prior usage stays conservatively charged. Repeating is explicit.
            conn.execute(
                "UPDATE runs SET tokens=tokens+reserved_tokens,reserved_tokens=0,usage_unknown=true WHERE id=?",
                (run_id,),
            )
            conn.execute(
                "UPDATE llm_calls SET status='acknowledged_retry' WHERE run_id=? AND status IN ('pending','uncertain')",
                (run_id,),
            )
        from .jobs import event

        event(
            conn,
            run_id,
            "owner",
            "resume_requested",
            {
                "duplicate_call_acknowledged": body.acknowledge_duplicate_call,
                "budget": body.budget.model_dump() if body.budget else original["config"]["budget"],
            },
        )
        row = conn.execute(
            """UPDATE runs SET status='queued',error=NULL,updated_at=now()
            WHERE id=? AND status IN ('waiting_for_quota','paused') AND NOT cancel_requested RETURNING *""",
            (run_id,),
        ).fetchone()
        if not row:
            raise HTTPException(409, "Only quota/config-paused runs can resume")
        conn.execute(
            """UPDATE jobs SET status='queued',owner=NULL,lease_until=NULL,available_at=max(now(),available_at),
            attempts=0,error=NULL WHERE target_id=? AND kind='research'""",
            (run_id,),
        )
        return row


@app.get("/api/runs/{run_id}/report", dependencies=[Depends(access)], response_class=PlainTextResponse)
def report(run_id: UUID):
    row = one("SELECT report FROM runs WHERE id=?", (run_id,))
    if not row or not row["report"]:
        raise HTTPException(404, "Report not ready")
    return PlainTextResponse(
        row["report"],
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="research-{run_id}.md"'},
    )
