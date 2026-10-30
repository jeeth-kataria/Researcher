# ADR 004 — SQLite local persistence and Groq primary provider

Status: accepted by explicit user request, superseding the PostgreSQL requirements in
ADRs 001–003 and the original specification where they conflict. Preserve that original
specification as history. This is an intentional product architecture change, not a
SQLite fallback claiming to exercise PostgreSQL semantics.

## Decision

Use Python's SQLite with WAL, foreign keys, FULL synchronous durability and a 15-second
busy timeout. One local file holds relational metadata, JSON artifacts, 384D embeddings,
FTS5 and LangGraph SqliteSaver checkpoint tables. SQL schema is versioned with user_version
and initialized explicitly. No database server, pgvector, SQLAlchemy, Alembic, Docker,
Redis, or hosted database is required. The pinned saver transitively installs sqlite-vec;
retrieval does not load it or require a vector extension.

Keyword search uses FTS5 BM25 (lower score is better), literal Unicode OR terms, bounded
to 64 distinct terms. Exact cosine scans only eligible frozen-version vectors in batches
and retains the nearest 80 with a bounded heap. RRF combines keyword/vector ranks, then
applies source-text deduplication and per-paper diversity. This ranking changes from the
old PostgreSQL implementation; prior evaluations are not comparative evidence.

Write contexts acquire BEGIN IMMEDIATE before read/check/write sequences, so a race
cannot claim a job twice or exceed a collection count through a lost update. WAL permits
readers during a write; writes serialize. Parsing, embedding and provider requests run
outside write transactions. Renewable leases and fences reject stale owners. A separate
OS flock spans graph invocation and all resulting checkpoint writes; process death
releases it. This revision supports a macOS/Linux local filesystem, not network-shared
SQLite files, cross-host writers, Windows locking or a horizontally scaled API.

Groq is the primary default in RunInput and the UI; fixture is always explicit. Use
revision-configured openai/gpt-oss-120b, with openai/gpt-oss-20b as an explicitly configured
allowlisted alternative. Official Groq docs list both with free limits and strict
structured outputs (checked 2026-10-30); actual account access and quality still require
live verification. Strict wire objects require every property and disallow extras;
full Pydantic constraints and evidence/role checks remain local. No built-in hosted tools
or hidden provider/model fallback. Runs freeze their model ID; resume uses that same ID.
Gemini remains an explicitly selected secondary provider.

Both SDK and transport retries are disabled for Groq. A 429 honors Retry-After and persists
a quota pause. Known configuration/context rejections pause without automatic retries.
Uncertain network/response/validation outcomes persist an ambiguous call and require an
explicit duplicate-quota acknowledgement before retry. Provider keys stay in server .env;
free-plan acknowledgment is required, and the app cannot infer billing from a key.

## Alternatives and consequences

Keeping local PostgreSQL was the smallest code change and better suits multiple concurrent
writers or a hosted API/laptop worker split. User prioritized removing database-server
setup. FAISS or a second vector store would split evidence/index ownership; exact ranking
is simpler for a bounded local corpus, with CPU cost to be measured on real papers.

A SQLite file on a laptop cannot be directly shared with an independently hosted API.
Current supported deployment is a public static showcase plus private local research.
Live public jobs would require a deliberately redesigned storage/coordination boundary.
No migration of existing PostgreSQL data is provided: back it up and re-ingest PDFs into
a new SQLite database, or implement/review a separate export/import tool if needed.
