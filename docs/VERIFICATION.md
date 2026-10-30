# Verification ledger — 2026-10-30

## What actually ran

Environment: macOS arm64, Python 3.12.2 in the project uv environment (Python 3.11.9
also available), Node 20.19.1, 10 logical CPUs. RAM capacity introspection was denied.
About 38 GiB disk was free initially. No GPU was used or assumed. Installed worker
Python environment measured about 1.4 GiB; its uv cache another 1.4 GiB. Model weights
are separate from those dependencies.

| Check | Actual outcome |
|---|---|
| Read complete original specification; inspect empty workspace | Completed |
| `uv sync --cache-dir .data/uv-cache --extra dev --extra worker --locked` | Passed, 181-package resolved lock graph, core + CPU worker extras installed |
| `npm install` / npm lock generation | Passed; exact frontend versions and integrity lockfile |
| Project `python -m compileall -q backend scripts migrations` | Passed |
| Project `pytest -q` | **19 passed, 7 skipped**; skips are real PostgreSQL cases requiring RGI_TEST_DATABASE_URL |
| `ruff check backend scripts migrations` | Passed |
| TypeScript + Vite normal/demo production builds | Passed; final patched dependency rerun recorded below |
| Chromium example browser flows | **4 passed** after UI revision: evidence/PDF/export/reload; matrix/mobile retrieval; orchestration/source/walkthrough; single-researcher quota-paused state |
| Full local browser upload/ingest/retrieval/fixture run | Written, opt-in, **not run** without PostgreSQL/API/worker |
| Official Gemini SDK with mock HTTP transport | Passed structured request/response and 429 no-retry contracts; **not a live provider run** |
| Original fixture PDF baseline parsing | All three parsed with pinned pypdf 5.6.0; real PDF bytes, invented source content |
| `rgi.evaluate --offline` | Six deterministic function comparisons (2 draft cases × 3 modes); not Postgres/LLM benchmarks |
| Worker imports | Docling and SentenceTransformers imports passed after install |
| Read-only/owner-token/secret-safe health tests | Passed using FastAPI TestClient |

Browser tests used a cached Chromium via ignored `.env.test.local` executable setting.
The in-app browser connector was not callable; repository Playwright ran independently.
Screenshots were rendered and visually inspected. PDF.js rendered the original page
(canvas 595×842); no bounding boxes were fabricated for pypdf/static fixtures.

## Blocks and exact remaining verification

**PostgreSQL/pgvector:** Docker client exists but daemon is offline. Native Homebrew
PostgreSQL 16.9 `initdb` was attempted in the workspace; sandbox denied System V shared
memory (`shmget: Operation not permitted`). No database migration, hybrid PostgreSQL
search, locking race, lease recovery or PostgreSQL checkpoint success is claimed.
Seven dedicated integration tests cover these, quota pause/resume, explicit ambiguous-call
acknowledgement graph restart and checkpoint-session serialization; run them with a real disposable RGI_TEST_DATABASE_URL.
SQLite is not used. The memory-checkpoint unit test is not a substitute.

**Model assets:** pinned worker packages installed and imported. Docling conversion
was attempted on three fixture PDFs but failed fetching `ds4sd/docling-models` v2.2.0
because Python network DNS was blocked. BGE load was attempted and failed for the same
reason. No BGE vectors, actual BGE tokenizer test, Docling source boxes, or full parser
comparison success is claimed. The implementation now explicitly requires a complete
revision-pinned BGE snapshot to prevent SentenceTransformers' automatic pooling fallback.
Run `uv run python scripts/prefetch_assets.py` on a host with permitted model downloads,
then measure the pipeline and run real database ingestion. Some shell curl metadata
requests succeeded via permitted commands; that does not verify Python model loading.

**Gemini:** no real key supplied, no live request made, no quota consumed. Mock transport
tests caught/fixed SDK HttpOptions and schema compatibility. Configure server key and
free-tier acknowledgement only after checking actual account billing and quotas, then
run an explicit real provider investigation. Current free-model listing was verified in
official docs, but actual account access remains unknown. Real scientific support is
unverified until human review; fixture completion cannot prove it.

**Hosted deployment:** not requested or attempted. Static demo build is prepared.
Mode C has explicit remaining storage/auth/query-embedding/memory/connection gates;
Docker API image build and hosted resource sizing are unverified. No paid account,
card, upgrade, hosted worker or external publication was created.

## Measurements and interpretation

`evaluation/pipeline-measurements.json` contains actual measured pypdf parse times
(~0.001–0.070 seconds on tiny one-page PDFs) and cumulative process peak RSS (~44 MiB).
Docling attempts reached ~578 MiB process peak **before asset-fetch failure**; that is
neither a successful parsing benchmark nor a recommended RAM capacity. Imports, warm
caches and process lifetime affect these numbers. These do not estimate large-paper
or BGE memory needs. Model/runtime sizing remains pending.

`evaluation/results.fixture.json` reports actual fixture function elapsed times/call
counts and structural citation checks. All model tokens are zero because no LLM ran.
Draft relevance annotations remain pending human review. Human factual support and
false-candidate-gap rates have zero judged denominators and null values. No conclusion
about multi-agent superiority, scientific accuracy or novelty is justified.

## Build fixes discovered by verification

- Pinned LangGraph 0.4.8 forbids a stage name matching a state field: prefix stage names.
- Gemini 1.20 does not support newer HttpRetryOptions: use its documented HttpOptions
  with zero-retry HTTP transport. No hidden SDK provider fallback.
- Gemini wire schema rejects additionalProperties: resolve Pydantic references and send
  supported schema subset; full strict local validation remains in place.
- Pinned PostgresSaver convenience constructor uses prepare_threshold=0 (always prepare):
  construct its supported psycopg connection with prepare_threshold=None explicitly.
- Upgraded Vite and Playwright within compatible stable lines after npm advisories;
  final audit/build/test outcomes are appended after the checks finish.

Initial default uv-cache writes/network metadata requests were restricted. An attempted
curl sandbox escalation was automatically rejected because sandbox approvals are disabled.
No confirmation was requested. Dependency installation later succeeded through permitted
uv/npm commands using a workspace cache. These initial failures are not current install
blockers and did not justify abandoning independent implementation.

## Final dependency and interface checks

Final frontend pins: Vite **6.4.5**, Playwright **1.55.1** (stable compatible Node lines;
upgraded to resolve current advisories). `npm install` reports **0 vulnerabilities**
including development dependencies. Final `npm run build -- --mode demo` passed with
Vite 6.4.5. After the UI revision, lazy loading PDF.js produces a **244 kB main bundle**
(75 kB gzip), **366 kB PDF viewer chunk** and a ~1.38 MB PDF worker. The main build no
longer emits a >500 kB chunk advisory.
Final `npm test`: **4 passed** in Chromium after the UI revision. The full local
ingestion browser case remains opt-in/unrun. Test-owned servers were stopped after QA.

A final reliability review added session advisory locking around graph execution to
serialize checkpoint writes after lease replacement. A seventh real-PostgreSQL test
covers that window; it remains skipped here along with the other database tests.
Final backend count is **19 passed, 7 skipped**. The application uses direct/session
connections for this reason; transaction poolers are explicitly unsupported.
