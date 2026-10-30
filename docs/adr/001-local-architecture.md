# ADR 001 — local monorepo and durable execution (accepted)
Requirement: zero required spend, inspectable evidence, resumable laptop execution.
Choice: FastAPI + sync psycopg transactions; separate Python worker; PostgreSQL 16
with pgvector; React/Vite static client; LangGraph PostgresSaver for research state.
SQL migrations via Alembic, SQLAlchemy used only by migration tooling. Explicit SQL
makes atomic SKIP LOCKED claims and RRF inspectable. Redis/Celery and managed agent
hosting add operations without evidence of throughput need. SQLite cannot exercise
pgvector, FTS or claims and is not a fallback. Revisit at measured queue contention.

Requirement: preserve sources and CPU path. Docling default with OCR disabled, pypdf
explicit lightweight baseline; BGE-small CPU, 384D, pinned revision. File hashes plus
processing identity identify immutable document versions; a different parser/model
creates a new version. Tables retain exported text and item IDs. Exact search first;
HNSW only after measured corpus growth. Fixture embeddings occupy a separate identity
and cannot enter a real Gemini run. Revisit parser/chunk parameters after evaluated
recall and source-layout quality; no universally best chunk length is claimed.

Requirement: cost and reliable citations. Gemini official SDK, one call at a time,
explicit key and free-tier acknowledgement, no fallback; fixtures are an independent
provider. Account billing cannot be verified by API key inspection: owner must check
AI Studio. Structured schema does not prove support; deterministic citation checks
and a separately recorded skeptical judgment both matter. Human review still needed.

Requirement: public safety. Local loopback and explicit CORS; optional server-side
owner bearer token. Read-only mode rejects all writes. Static export has no API or
keys. No hosted mutation mode without owner token. Optional storage/discovery/Ollama
are deferred; local storage and corpus-only coverage are sufficient for version one.

Environment: macOS arm64, Python 3.11.9, Node 20.19.1, 10 logical CPUs, ~38 GiB disk
free on inspection. RAM query denied by sandbox; RAM capacity is unknown. Docker daemon
offline; native Homebrew PostgreSQL 16.9 available. Record actual check results in
VERIFICATION.md. No GPU assumed. Dependency versions selected from stable compatible
Python 3.11 / Node 20 lines, with lockfiles for the resolved transitive graph.

Final compatible frontend patch selection: Vite 6.4.5 and Playwright 1.55.1 replace the
initial older patches after npm's advisory evidence. Node 20.19.1 build/browser checks
passed. Exact pins and npm integrity lock remain checked in. Python core/worker pins
and the uv transitive graph resolved and installed; model assets are a separate verified
boundary, not silently bundled in the package lock.
