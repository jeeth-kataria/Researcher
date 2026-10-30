# Local setup — no database server

Use Python 3.11–3.13, uv and Node 20.19+. The worker's supported hosts are macOS/Linux
with a local filesystem supporting SQLite WAL and flock. No Docker, PostgreSQL or
cloud account is required. Read README for exact API/worker/frontend commands.

1. Copy `.env.example` to `.env` without overwriting an existing configuration.
2. `uv sync --locked --extra dev --extra worker` (optional `--cache-dir .data/uv-cache`).
3. `uv run python scripts/init_db.py` creates/versions SQLite + FTS5 + checkpoints.
4. Start API, separate worker and frontend in three terminals as in README.
5. First choose pypdf + fixture embedding and explicitly submit a fixture run. Then
   download actual model assets and configure Groq before testing real research.

`RGI_DATABASE_PATH` defaults to `.data/researcher.sqlite3`. `RGI_STORAGE_DIR` defaults to
`.data`. Keep both on local disk. SQLite needs FTS5 and RETURNING (SQLite 3.35+); current
Python builds include them, and init/tests fail visibly if unavailable. Configuration
checks refuse missing initialization rather than silently creating an empty app database.
Use init before starting services, not concurrently with requests. Existing schema
versions other than the supported version fail explicitly; future migrations need backups.

## Existing installations

The old `RGI_DATABASE_URL`, Compose and Alembic startup are retired. This revision does
not convert an existing PostgreSQL database. Keep its backup and original files, create
a fresh SQLite path, and re-ingest PDFs. Do not delete the old database to try the new
one. A dedicated reviewed export/import would be needed to preserve old run histories.
The unchanged original specification and superseded ADRs are historical references.

## Local assets and resource sizing

Docling and BGE are pinned CPU models; run `uv run python scripts/prefetch_assets.py` on
a network permitting model downloads. Cache directories live under `.data/models` unless
explicitly overridden. No local generative model or GPU is downloaded. pypdf + fixture
requires neither weights nor an LLM key. It cannot measure scientific quality.

Small original PDFs parsed with pypdf have measured timings in
`evaluation/pipeline-measurements.json`. Prior Docling/BGE asset downloads failed in the
sandbox, so those values are not successful semantic ingestion or capacity benchmarks.
Exact vector search is linear in eligible passage count; measure real corpora before
increasing the 50-paper bound. One worker is supported; keep writes short.

## Back up and restore

Stop API/worker for a coordinated backup of database + PDF/artifact files:

```sh
uv run python scripts/backup_db.py .data/backups/researcher.sqlite3
```

The script uses SQLite's backup API to include committed WAL contents and refuses to
overwrite an existing destination. Copy `.data/pdf`, `.data/parsed` and any needed
index caches separately. To restore, stop services, choose a clean path/directory,
restore the database and matching source files, set database/storage paths, then restart.
Do not overwrite an active database with live `-wal`/`-shm` sidecars. Lock files contain
no application data. Never place a live database in Dropbox/NFS/network-shared storage.

## Public access

Bind local services to loopback. Optional `RGI_OWNER_TOKEN` provides server-verified
owner bearer access. Public static demo requires none of the owner's files, tokens or
processes. A hosted frontend cannot automatically call a visitor's localhost or access
the owner's SQLite file. See DEPLOYMENT.md before considering live public submissions.
