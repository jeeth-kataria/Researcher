# Learn the current implementation

## 1 — Foundation and dispatch

Flow: browser → FastAPI validation → SQLite job row → separate worker. Read config.py,
db.py, schema.sql, jobs.py and worker.py. Initialize with `uv run python scripts/init_db.py`.
Health reads an actual worker heartbeat. API requests never own the research job.

Why SQLite? User chose simpler single-laptop setup. WAL permits readers while one
writer commits. BEGIN IMMEDIATE serializes check/claim/update sequences. Leases/fences
handle expired ownership; OS locks additionally protect post-node checkpoint writes.
Run `uv run pytest -m integration -q` to exercise real files, not an in-memory mock.

## 2 — Evidence and retrieval

Read ingest.py, storage.py, embeddings.py and retrieval.py. Hash + processing identity
creates immutable versions. The CPU parser emits original items/pages/boxes; pypdf is
an explicit no-layout baseline. The chunker uses actual token counts and keeps exact
source text. BGE vectors are revision-pinned; fixture hashes are only software controls.
SQLite FTS5 BM25 + exact cosine ranks combine with RRF, deduplication and paper diversity.
Scores are not factual confidence. A frozen manifest fixes eligible document versions.

Run the original fixture workflow with `uv run python scripts/demo.py` after starting
API/worker in pypdf/fixture mode. It exercises actual SQLite ingestion and API retrieval.
`npm run demo` is instead a static fixture explorer; it does not exercise the worker.

## 3 — Structured generation and baselines

Read schemas.py, provider.py, tools.py, evidence.py and research.py. Groq is primary;
Gemini is explicitly optional. Strict wire JSON does not establish quote validity or
semantic support. Pydantic and evidence/role checks enforce independent local rules.
One call persists intent before network I/O and response afterward. That crash window
cannot guarantee exactly-once external execution. Unknown outcomes pause for explicit
acknowledgement; no silent account/model/provider fallback spends new quota.

RAG generates once. Single uses one researcher persona across extraction/self-review/
proposal continuations. Neither is mislabeled as an independent multi-agent review.
Default tests use fake keys only with mock HTTP; no real provider quota is consumed.

## 4 — Bounded multi-role graph

Read Investigation methods then build_graph. Retrieve → lead plan → literature → methods
→ lead candidates/counter-search/context → skeptical review → proposals → report. Five
personas, six model stages; sequential execution. Graph state uses SqliteSaver in the same
database file, separately from dispatch ownership. Cached outputs/checkpoints reduce
replay but cannot prove an uncertain external call was never charged.

Run restart/quota/ambiguity integration tests. Explain why job fencing alone does not
cover checkpoint writes that occur after a node returns; run_lock spans both. Closing
or killing the process releases the OS lock. Do not use network-shared SQLite files.

## 5 — Product, provenance and evaluation

Read UI.md and Orchestration.tsx. Stage states come from persisted event kinds plus run
status. A manual fixture cursor is labeled and cannot masquerade as live agent activity.
The original PDF viewer lazily loads PDF.js; only real parser boxes are highlighted.

`npm test` checks the static explorer. `npm test -- --config playwright.local.config.ts`
starts actual local API/worker/SQLite/Vite with synthetic inputs. Offline evaluator
outputs do not establish research quality. Human support/false-gap metrics stay null
until judgments exist. Before interviews, review VERIFICATION.md and explain every
pending live-provider/model limitation rather than claiming all paths have run.
