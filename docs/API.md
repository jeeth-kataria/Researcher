# API reference

Interactive OpenAPI: http://127.0.0.1:8000/docs. All data routes require the configured
owner bearer token if nonempty; health is sanitized/public. Read-only rejects mutations.
Default local mode trusts one owner, not multiple authenticated tenants.

| Method | Path | Purpose |
|---|---|---|
| GET | /api/health | API/database/real worker status, no secrets |
| GET / POST | /api/collections | List / create named scope |
| GET / POST | /api/collections/{id}/papers | Version/status list / bounded PDF multipart title+file |
| GET | /api/collections/{id}/search?q=...&k=8&diversity=3 | Scoped keyword/vector/fused rank inspector |
| GET | /api/collections/{id}/evidence/{id} | Exact passage + neighbors |
| GET | /api/versions/{id}/pdf | Original bytes for that immutable version |
| GET / POST | /api/runs | History / submit async job; returns run ID immediately |
| GET | /api/runs/{id} | Status, manifest, result, persisted events |
| POST | /api/runs/{id}/cancel | Request stop between steps |
| POST | /api/runs/{id}/resume | Quota/config pause recovery; optional validated budget and explicit uncertain-call acknowledgement |
| GET | /api/runs/{id}/report | Markdown download when report is ready |

Mutating public modes are not supported without private server-side owner access.
A malformed LLM result or invalid evidence fails validation instead of inventing a
citation. Provider errors expose safe categories, not raw request prompts or keys.

The checkpoint schema is created only by `scripts/setup_checkpoints.py`. The API does
not create tables at startup, ingest inline, or launch process-local research tasks.

Primary research provider is `groq` (the RunInput default). Explicit alternatives: `gemini`, `fixture`. Health includes `database_engine: sqlite`, `primary_provider: groq`, and sanitized configured flags. Keys never appear in health. SQLite must be initialized with `scripts/init_db.py` before services start.
