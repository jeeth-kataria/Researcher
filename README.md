# Research Gap Investigator

A local evidence-first research workbench: upload papers, inspect hybrid retrieval,
compare methods, challenge provisional candidate gaps, and export falsifiable
experiment proposals with source passages. Required spending: **₹0**. No cloud account
is required for local development or the static example. No experiment is executed.

**Verification status:** the interface, deterministic workflow, PDF baseline and
SDK mock-transport contracts have been exercised. Real PostgreSQL/pgvector and live
Gemini execution require the checks described below; see [the verification ledger](docs/VERIFICATION.md).
Fixtures are **not real research**. Nothing here establishes scientific novelty.

## Start the read-only example (no API, database, key, or worker)

Requires Node 20.19+ and npm. From the repository root:

```sh
cd frontend
npm ci
npm run demo
```

Open http://127.0.0.1:5173. Start in Orchestration: select a stage to inspect its saved
output and related artifact evidence, or choose **Walk through fixture** to step through
synthetic records without executing agents. The light neumorphic interface uses raised
panels, inset controls, visible focus outlines and explicit textual status labels.
Inspect Findings, Literature matrix, Gap review and Activity;
click a source to render its original PDF page; export Markdown. All three PDFs are
original synthetic fixtures. A deliberate false candidate is rejected and a toy
experiment is proposed. This is generated fixture output, not a recorded live run.

Build a static export with `npm run build -- --mode demo`; serve `frontend/dist` using
any static server. It contains inspectable sources and requires no live backend.

## Start the local application

Requires Python 3.11–3.13, uv, Node 20.19+, and PostgreSQL 16 with pgvector. Use Docker
Engine/Compose or Podman-compatible Compose; a paid Docker Desktop subscription is
not required. Native installation is documented in [LOCAL_SETUP.md](docs/LOCAL_SETUP.md).
Run commands from the root unless a directory is specified:

```sh
cp .env.example .env
uv sync --locked --extra dev --extra worker
# If the default uv cache is restricted, append --cache-dir .data/uv-cache.
docker compose up -d db
uv run alembic upgrade head
uv run python scripts/setup_checkpoints.py
```

Use three terminals, all inheriting the root `.env`:

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

Check http://127.0.0.1:8000/api/health (worker availability is a real heartbeat),
http://127.0.0.1:8000/docs and http://127.0.0.1:5173. Create a collection, upload PDFs,
wait for each ready/failed outcome, inspect retrieval, and submit an investigation.
Heavy parsing/embedding stays in the separate laptop worker. Polling does not own the
run; closing the browser does not cancel it.

The default pipeline uses **Docling, OCR off**, and revision-pinned **BGE-small CPU**.
The first use downloads parser/embedding assets, never a generative model. See the
resource measurements and limits below before large corpora. The API's query encoder
loads BGE locally as well; hosted API deployment is not enabled or sized here.

### Deterministic offline workflow with real PostgreSQL

Set these values in `.env` before starting API and worker:

```dotenv
RGI_PARSER=pypdf
RGI_EMBEDDER=fixture
```

Then `uv run python scripts/demo.py` ingests the original fixture PDFs, retrieves real
Postgres records, submits a persisted five-role **fixture** run, opens evidence through
the API, and saves `.data/demo-report.md`. It requires a real running database and worker.
The fixture embedder is a deterministic lexical hash, not a semantic model. Never
benchmark scientific quality with it. New parser/embedder settings create new document
versions; an existing report keeps its old evidence.

### Real Gemini run (optional, no paid dependency)

Supply **server-side** `.env` values:

```dotenv
RGI_PARSER=docling
RGI_EMBEDDER=bge
RGI_GEMINI_API_KEY=your_AI_Studio_key
RGI_GEMINI_MODEL=gemini-2.5-flash
RGI_FREE_TIER_ACK=true
```

Set the acknowledgement only after confirming **Free tier, billing disabled, and
active model quotas** in your AI Studio account. The app cannot infer billing status
from a key. Official [pricing](https://ai.google.dev/gemini-api/docs/pricing) lists free
standard input/output for this model; [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
are account-specific. Do not enable billing or automatic upgrades. Free usage may be
used to improve Google's products; review this before submitting private papers.
Restart API/worker, reingest with the BGE pipeline, and explicitly choose Gemini in
research setup. Fixture indexes are rejected for real research. No model/account/provider
fallback occurs. A 429 persists `waiting_for_quota`; check your quota before Resume.
`uv run python scripts/demo.py --provider gemini` is an explicit opt-in that consumes
free quota on synthetic source documents; it is not a real literature investigation.

No credentials have been supplied or live Gemini call claimed in this build.

### Configuration and recovery

`.env.example` lists all settings. Optional `RGI_OWNER_TOKEN` enables server-verified
bearer access; enter it in the UI's Owner access panel (memory only). Keys and database
credentials never belong in `VITE_` variables. Default binding is loopback. Use
`RGI_READ_ONLY=true` to reject every mutation; static demo has no mutation backend.

Budgets default to 10 calls, 60,000 total token accounting ceiling, 1,800 output tokens,
12 tools, 2 followups, 1 review round, k=8, maximum 3 passages/paper. These are application
limits, not provider quotas. Calls are sequential. Token usage is measured when the
provider supplies it; otherwise shown unknown and conservatively reserved. Daily quota
exhaustion never creates an automatic retry loop. Cancel is checked between steps;
an in-flight external request may complete.

A model call persists `pending` before network I/O. A crash after sending but before
saving its result has an unknown outcome. Resume requires the checkbox acknowledging
possible duplicate quota consumption. Unknown usage stays conservatively charged.
The paused-run controls also allow explicit budget changes. Example API request:

```sh
curl -X POST http://127.0.0.1:8000/api/runs/RUN_UUID/resume \
  -H 'Content-Type: application/json' \
  -d '{"acknowledge_duplicate_call":true}'
```

The API does not automatically retry uncertain external calls. See [reliability](docs/ARCHITECTURE.md).

## Verify and evaluate

```sh
uv run pytest -q
cd frontend
npm run build
npx playwright install chromium
npm test
```

Default tests do **not** contact Gemini. PostgreSQL tests skip unless you supply a
**dedicated empty disposable database**, with pgvector, via `RGI_TEST_DATABASE_URL`:

```sh
RGI_TEST_DATABASE_URL=postgresql://rgi:rgi@127.0.0.1:5433/rgi_test uv run pytest -m integration -q
```

Create `rgi_test` first using your database administrator. Tests create schemas/tables;
do not point them at personal data. For the full browser ingestion flow, start API and
worker in fixture mode, then run `RGI_E2E_LOCAL=1 npm test` inside `frontend`.
If using an already installed Chromium, set `RGI_BROWSER_EXECUTABLE` or put that value
in ignored `frontend/.env.test.local`; use the Playwright-matched browser normally.

```sh
uv run python -m rgi.evaluate --offline --output .data/evaluation.fixture.json
uv run python -m rgi.evaluate --collection COLLECTION_UUID --provider fixture
# Only after explicit quota/account configuration:
uv run python -m rgi.evaluate --collection COLLECTION_UUID --provider gemini
uv run python scripts/measure_pipeline.py fixtures/paper-a.pdf fixtures/paper-b.pdf fixtures/paper-c.pdf
```

See [evaluation protocol](evaluation/README.md). Draft labels are pending human review.
Published fixture measurements are plumbing checks, not proof that multiple agents
outperform RAG. Human support/false-gap metrics remain null when unjudged. See
[evaluation/pipeline-measurements.json](evaluation/pipeline-measurements.json) for actual
baseline parse latency and peak RSS, explicitly labeled by environment and parser.
No GPU is needed; full Docling/BGE resource needs are not inferred from pypdf results.

## Walk through the code

1. `api.py` validates bounded uploads, stores content hashes and dispatches a job.
2. `jobs.py` claims rows atomically with `FOR UPDATE SKIP LOCKED`, leases and heartbeat.
   Fenced transactions reject stale owners. Dispatch is at least once.
3. `ingest.py` parses source items, retains pages/boxes/headings, splits using the real
   embedding tokenizer, and commits passages/vectors transactionally. `embeddings.py`
   pins BGE revision and refuses silent truncation or mixed index identities.
4. `retrieval.py` scopes versions/collections and fuses exact cosine ranking with
   PostgreSQL full-text `ts_rank_cd`. This is not BM25 or calibrated confidence.
5. `research.py` implements functions, then schedules RAG, single-agent or five-role
   stages with LangGraph and PostgreSQL checkpoints. The reviewer precedes experiments.
6. `evidence.py` rejects missing/cross-version IDs, mismatched quotes and invalid stage
   dependencies. Separate support review is recorded; it is not scientific proof.
7. `report.py` exports the frozen manifest, matrix, findings, review objections,
   proposals, scope limits and inspectable references as Markdown.

Architecture/ADRs, milestone learning, accurate interview answers, deployment boundaries
and all outstanding verification are in [docs](docs/ARCHITECTURE.md).

Proposed resume bullet (review and understand before using): “Built an evidence-first
research workbench with FastAPI, PostgreSQL/pgvector, local PDF ingestion, hybrid
retrieval, bounded LangGraph workflows, source validation, and a React evidence viewer;
added deterministic tests and a labeled static demo.” No invented accuracy, speed,
publication or cost savings claims.

This application was generated with Codex and is intended for Jeeth to study, review
and extend. It does not imply Jeeth personally authored every generated line.
