# Research Gap Investigator

A local research workbench: ingest papers, inspect hybrid retrieval, compare methods,
challenge provisional gaps, and export falsifiable experiment proposals with citations.
**₹0 required spending. SQLite is local; Groq is the primary LLM provider.** Heavy PDF
processing, embeddings and orchestration run on your laptop. Gemini is an optional
explicit secondary provider. Fixtures are synthetic software tests, not real research.

The switch from PostgreSQL/Gemini follows the user's explicit architecture revision;
see [ADR 004](docs/adr/004-sqlite-and-groq.md). The original prompt remains unchanged as
history. No PostgreSQL, Docker, cloud database or GPU is required.

## Explore the public-style example without a key or backend

Requires Node 20.19+ and npm:

```sh
cd frontend
npm ci
npm run demo
```

Open http://127.0.0.1:5173. The light neumorphic interface opens in Orchestration.
Select stages to inspect saved outputs and related artifact evidence; **Walk through
fixture** steps through synthetic records without running agents. Inspect Findings,
Literature matrix, Gap review and Activity, open original PDF pages, or export Markdown.
All three papers are original invented fixtures. No scientific novelty is established.

Static export: `npm run build -- --mode demo`, output `frontend/dist`. No environment
variables or external service are needed. [Deployment plan](docs/DEPLOYMENT.md).

## Start the complete local application

Requires Python 3.11–3.13, uv and Node 20.19+. Supported worker hosts: macOS/Linux, with
a local filesystem supporting SQLite WAL and OS file locks. Run from the repository root:

```sh
cp .env.example .env
uv sync --locked --extra dev --extra worker
# Add --cache-dir .data/uv-cache if the default uv cache is restricted.
uv run python scripts/init_db.py
```

This explicitly creates `.data/researcher.sqlite3`, the FTS5 index and durable graph
checkpoint tables. Initialization is safe to repeat. Use three terminals:

```sh
uv run uvicorn rgi.api:app --host 127.0.0.1 --port 8000
```

```sh
uv run python -m rgi.worker
```

```sh
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173; API health: http://127.0.0.1:8000/api/health. Create a
collection, upload PDFs, wait for ready/failed outcomes, inspect retrieval, then submit
an investigation. Closing the browser does not cancel a persisted job. The heartbeat
reflects actual worker availability. SQLite metadata alone does not contain PDF bytes:
keep the local `.data/pdf` and parsed artifacts with the database.

### Run the deterministic workflow first

Set these values in `.env` and restart API/worker:

```dotenv
RGI_PARSER=pypdf
RGI_EMBEDDER=fixture
```

No model downloads are needed. In research setup, **explicitly select Deterministic
fixture**; Groq remains the default and is disabled for submission until configured.
Or run `uv run python scripts/demo.py`: the script uploads all three invented PDFs via
the API, waits for the separate worker, searches real SQLite records, submits a persisted
fixture investigation, verifies evidence access, and saves `.data/demo-report.md`.
The fixture embedder is lexical hashing, not semantic research. The script never selects
a live provider unless passed `--provider groq` or `--provider gemini` explicitly.

### Enable real Groq research

Set server-side `.env` values:

```dotenv
RGI_PARSER=docling
RGI_EMBEDDER=bge
RGI_GROQ_API_KEY=your_Groq_key
RGI_GROQ_MODEL=openai/gpt-oss-120b
RGI_FREE_TIER_ACK=true
```

Set the acknowledgement only after checking your account's **Free plan, billing and
active model quotas**. The app cannot infer billing status from a key. Current official
[Groq limits](https://console.groq.com/docs/rate-limits) list the allowlisted 120B and 20B
models on the free plan; [structured outputs](https://console.groq.com/docs/structured-outputs)
are supported. Actual limits are account-specific. No paid upgrade is required or
performed. An explicit `RGI_GROQ_MODEL=openai/gpt-oss-20b` selects the smaller alternative;
no automatic model/account/provider switch occurs. One configured model serves all roles.

Test the key/network independently of PDFs and local models with
`uv run python scripts/check_groq.py`. This explicitly sends one small live request and
consumes free quota when successful. It prints sanitized status/usage, never the key.
Configuring a key alone does not start calls; static demo/fixture mode never uses Groq.

Run `uv run python scripts/prefetch_assets.py` to download pinned Docling/BGE assets.
Restart services, re-ingest papers using BGE and select Groq. Old fixture indexes cannot
enter a real-provider run. Parser/embedding identity changes create new immutable document
versions. Groq requests use strict structured output, bounded generation and local
citation/role validation. A model's schema compliance does not prove factual support.

Six role calls, follow-up passages and cumulative context consume free quota. A 429
persists waiting_for_quota and respects Retry-After. Reduce retrieval/output budgets for
small token-per-minute allowances; lower budgets do not guarantee account availability.
Unknown call outcomes require explicit acknowledgement before retry. No live Groq or
Gemini call has been verified without credentials. Synthetic demo papers remain synthetic
even if a live provider reads them.

Gemini remains optional: configure `RGI_GEMINI_API_KEY`, leave
`RGI_GEMINI_MODEL=gemini-2.5-flash`, verify its free-tier account settings and explicitly
select Gemini. It is never a Groq fallback. Keep every key out of `VITE_` variables and Git.

## Verify

Default tests consume no LLM quota and require no database service:

```sh
uv run pytest -q
uv run ruff check backend scripts
cd frontend
npm test
npm test -- --config playwright.local.config.ts
npm run build -- --mode demo
```

SQLite integration tests use isolated temporary files and actually execute ingestion,
FTS/vector retrieval, claim races, lease recovery, on-disk checkpoints, restart,
cancellation, quota/ambiguity controls and process locks. The local Playwright config
starts an isolated SQLite/API/worker/Vite fixture stack itself (ports 8000/5173 must be
available); it uses `.venv/bin/python` installed by `uv sync`. No owner credentials or
model downloads are used. Default browser tests cover the static example. Install a
browser with `npx playwright install chromium` if needed; an existing compatible browser
can be selected via `RGI_BROWSER_EXECUTABLE`. [Verification ledger](docs/VERIFICATION.md).

## Recovery, budgets and security

`.env.example` lists all settings. Optional `RGI_OWNER_TOKEN` enables server-verified
bearer access; the UI keeps it in memory. `RGI_READ_ONLY=true` rejects all mutations.
The local API binds to loopback. No public laptop endpoint is created.
Configuration always loads the project-root `.env`. Relative database/storage paths
are also rooted there, so launching a script from `scripts/` does not lose credentials
or create a second data directory. Environment variables still override `.env` values.

Run defaults: 10 model calls, 60,000 conservative token-accounting ceiling, 1,800 output
tokens/call, 12 tools, 2 followups, 1 review round, k=8 and at most 3 passages/paper. These
are application ceilings, not provider quota guarantees. Real usage is shown when
supplied, otherwise unknown with conservative charging. Call/model configuration is
frozen per run. The UI offers cancel, explicit resume and budget controls. Cancellation
is checked between steps; an in-flight remote request may finish.

An intent is persisted before provider I/O. A crash after sending but before saving a
response has an unknown outcome. Resume requires the duplicate-call acknowledgement;
unknown prior usage remains charged. SQLite writes use short BEGIN IMMEDIATE transactions;
a separate per-run OS lock spans graph invocation/checkpoints without holding a database
write lock during provider calls. One worker is the supported configuration.

For a consistent database backup: `uv run python scripts/backup_db.py .data/backups/run.sqlite3`.
Stop API/worker while also copying PDF/artifact files for a coordinated restore. Do not
copy a live SQLite file alone and assume its WAL has been captured. See [local setup](docs/LOCAL_SETUP.md).

## Evaluate and understand

```sh
uv run python -m rgi.evaluate --offline --output evaluation/results.fixture.json
uv run python -m rgi.evaluate --collection COLLECTION_UUID --provider fixture
# Explicit opt-in, consumes free quota:
uv run python -m rgi.evaluate --collection COLLECTION_UUID --provider groq
```

Evaluation compares RAG, a single researcher's self-review and five-role investigation.
Fixture outputs are software controls; human support/false-gap judgments remain unfilled
until reviewed. No scientific novelty or multi-agent superiority is claimed. Real model
assets, provider quality and full-paper resource sizing remain separately verified work.

Flow: PDF → immutable version → leased worker → local chunks/embeddings → SQLite FTS5
BM25 + exact cosine RRF → bounded graph → skeptical review → citation checks → report.
A search miss is never evidence of universal novelty. Reports preserve source quotes,
unknowns, objections, provisional conclusions and falsifiable proposals.

- [Architecture](docs/ARCHITECTURE.md) and [UI observability](docs/UI.md)
- [Learning guide](docs/LEARNING_GUIDE.md) and [interview/resume guide](docs/INTERVIEW_GUIDE.md)
- [Requirements](docs/PROJECT_BRIEF.md), [progress](docs/PROGRESS.md), [API](docs/API.md)
- [Verification](docs/VERIFICATION.md), [deployment](docs/DEPLOYMENT.md), [official references](docs/OFFICIAL_REFERENCES.md)
