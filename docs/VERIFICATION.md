# Verification ledger — SQLite/Groq revision, 2026-10-30

Current architecture is explicitly amended by the user in ADR 004. Old PostgreSQL test
skips are historical, not the current backend's verification status. Tests below use
actual SQLite files; synthetic provider/content labels remain explicit.

## What actually ran

Environment: macOS arm64, project Python 3.12.2, Node 20.19.1, 10 logical CPUs. No GPU
was used. RAM introspection was restricted. The existing worker extras remain installed;
real model weight downloads are separate from dependency installation.

| Check | Actual result |
|---|---|
| `uv sync --cache-dir .data/uv-cache --extra dev --extra worker` | Passed; lock resolves 176 packages, adds Groq/SqliteSaver, removes PostgreSQL driver/vector/migration packages |
| `pytest -q` | **41 passed, zero skipped**, including actual file-backed SQLite integration |
| SQLite ingestion/retrieval | Original synthetic PDF bytes parsed by pypdf, immutable versions, real FTS5 BM25/exact cosine/RRF and scoped source context exercised |
| Dispatch/recovery | Atomic competing claims, expired-lease fencing, persisted fixture graph, cancellation, quota pause/resume and explicit ambiguous-call acknowledgement passed |
| Durability/checkpoint coordination | On-disk checkpoint resume avoids completed model-stage replay; fresh Python process reads saved rows; process-lock contention and death release passed |
| Initialization/backup | Idempotent schema init, FTS literal-query handling, real worker health and SQLite backup/integrity check passed |
| Workspace initialization | `scripts/init_db.py` passed; default SQLite health online, worker offline and Groq/Gemini unconfigured accurately reported |
| Groq official SDK mock HTTP | Strict request schema, response validation/usage, frozen model selection, one-request 429/Retry-After, known rejection and generated-output ambiguity passed |
| Gemini official SDK mock HTTP | Existing structured response and 429/no-retry contracts passed; optional secondary only |
| Static Chromium suite | **4 passed**: source/PDF/export/reload, matrix/mobile retrieval, orchestration walkthrough and quota-paused display |
| Local Chromium/CLI suite | **2 passed**: browser upload → worker → retrieval → fixture graph → reload; three-paper CLI demo via actual API/worker |
| TypeScript + Vite production demo build | Passed; ~244 kB entry (75 kB gzip), ~366 kB lazy PDF viewer and ~1.38 MB PDF worker |
| Ruff / whitespace checks | Passed; see repository commands |

Default tests make no live Groq/Gemini request. Mock-transport tests use fake keys with
the official installed SDK. The local browser suite starts isolated services with
keys explicitly cleared and separate state under `.data/e2e/`; its parser/embedder and
responses are fixtures. Its second test executes `scripts/demo.py`, retrieving three
original invented PDFs and saving `.data/e2e-demo-report.md` with fixture provenance.
This is now actual API/worker/SQLite plumbing validation, not a real literature study.

The browser tests used the cached Chromium executable configured in ignored local
test settings. The in-app browser connector remains unavailable; repository Playwright
was used. Earlier UI screenshots were inspected. The local flow confirmed Groq is the
initial selection, disabled without configuration, and fixture requires explicit choice.
The synthetic banner also remains on completed local fixture reports.

One initial `npm run test:local` launch was denied loopback binding by this sandbox.
The permitted `npm test -- --config playwright.local.config.ts` entrypoint subsequently
started the same isolated stack and passed. An initial browser locator failed despite
a visible Provider selector; explicit accessible naming fixed it and the flow passed.
No database/locking path was replaced with an in-memory substitute to obtain a pass.

## Remaining verification

**Groq account/live calls:** no real key supplied, no live call or quota consumed. Official
Groq docs list the default 120B and explicit 20B alternative under free limits and strict
structured outputs. Actual account access, billing state and quotas remain unknown.
The code cannot infer those from a key. Configure `RGI_GROQ_API_KEY`, choose/verify the
free model, acknowledge the free plan, then run an explicit real-provider investigation
on a semantically indexed corpus. Six sequential stages can exhaust token-per-minute
allowances; a pause/resume is expected behavior, not evidence of provider quality.

**Model assets:** prior Docling and SentenceTransformers package imports succeeded.
Actual Docling/BGE model assets failed to download because Python network DNS was blocked.
Those downloads were not reclassified as successful after switching databases. No real
BGE vectors/tokenizer test, Docling coordinates or semantic ingestion success is claimed.
Use `scripts/prefetch_assets.py` on a host permitting the pinned downloads and measure
real PDF processing. Fixture hashing cannot enter a real-provider research run.

**Scientific evaluation/capacity:** no human factual-support/false-gap judgments or
real-literature novelty validation exist. Draft labels remain pending review. Exact
vector ranking is linear in eligible corpus size; realistic latency/RAM sizing remains
pending, not inferred from three one-page synthetic papers.

**Deployment:** none executed. Current public option is the read-only static showcase.
Separate hosted API + laptop SQLite sharing is unsupported. Previous optional hosted
Postgres architecture is retired for this version. The slim API Dockerfile is retained
as unbuilt packaging; it has not been built or measured and is not the recommended local
startup or a claim of hosted BGE support. Native Windows locking is unsupported.

**Existing PostgreSQL data:** no automatic transfer is provided. The old database is not
modified. Back it up and re-ingest into a fresh SQLite file, or build a reviewed migration
if preserving old run history becomes required.

## Measurements retained from the original build

`evaluation/pipeline-measurements.json` records real pypdf parse times (~0.001–0.070 s)
and cumulative process RSS (~44 MiB) on tiny original synthetic PDFs. Docling import/fetch
attempts reached ~578 MiB before asset failure; this is not a successful parser benchmark.
`evaluation/results.fixture.json` contains six deterministic function comparisons, with
zero model tokens. It is not a SQLite retrieval benchmark or live provider evaluation.
Human support/false-gap metrics remain null with zero judged denominators.

## Reproduce

See README for init/start commands. `uv run pytest -q` includes the SQLite tests without
service credentials. `npm test` runs the four static flows; from frontend,
`npm test -- --config playwright.local.config.ts` runs the two isolated local flows.
No LLM quota is consumed by either suite. Live-provider tests remain explicit owner work.
