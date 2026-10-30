# Milestone learning guide
## 1 — foundation
Flow: browser → FastAPI validation → PostgreSQL job → independent worker. API health
and worker heartbeats are different signals. `claim()` uses row locks + SKIP LOCKED;
`fence()` prevents an expired owner writing job results. Runs freeze document versions.
Try `curl http://127.0.0.1:8000/api/health`. A database outage is reported honestly.
Q: Why not BackgroundTasks? A: process-local work disappears on API restart and has
no durable ownership. Q: Exactly once? A: no, leases give at-least-once dispatch.
Q: Why PostgreSQL? A: relational constraints, FTS, vectors and checkpoints in one
local service; this does not imply PostgreSQL is best for every scale or workload.

## 2 — evidence before agents
Flow: bounded upload → content hash + immutable version → durable ingest job → local
parser → item-aware tokenizer chunks → CPU vectors → one transaction → hybrid search.
Key functions: `upload`, `parse_pdf`, `chunk_items`, `ingest`, `search`, `context`.
Demo: start fixture-mode API/worker and use `uv run python scripts/demo.py`; or inspect
sources in the static example to learn navigation without a database. These demonstrate
different things: static source navigation does not validate PostgreSQL ingestion.
Q: Why token counts rather than character counts? A: model windows use tokens; headings
and special tokens consume capacity too. Q: Why retain model revision? A: vectors from
different preprocessing/models cannot safely share an index. Q: RRF confidence? A:
no, it fuses rank positions; no probability calibration is implied. Q: Why source boxes?
A: source navigation; parser regions can be larger than a quote, and absent boxes are
not invented. `pypdf` is the explicit baseline and has no region metadata here.

## 3 — baseline and reliable execution
Flow: run setup freezes corpus/config → queued job → retrieval → one researcher →
validated output → same-agent self-review/proposals → Markdown. Ordinary RAG is one generation.
Key functions: `create_run`, `Investigation.model_call`, `validate_output`, `render_report`.
Demo: `scripts/demo.py --mode rag` then `--mode single` on a dedicated local fixture
pipeline. Inspect calls, usage, manifest and citations rather than claiming quality.
Q: Does structured output mean true output? A: no, schema validity and scientific
support are distinct. Q: How prevent expensive replay? A: durable response cache plus
explicit unknown-outcome pause; it cannot guarantee no duplicate provider charge.
Q: How does quota recovery work? A: persisted waiting status and not-before time,
explicit owner resume, never another model/account. Current external call may finish
before cancellation takes effect.

## 4 — graph and five roles
Flow: retrieve → lead plan → literature coverage/followups → methods extraction →
lead candidates/counter-search/context → skeptical reviewer → experiment proposals →
report. Graph checkpoints use the same PostgreSQL service but separate tables and
connections from dispatch jobs. Stage names differ from state-field names to stay
compatible with pinned LangGraph 0.4.8. A pinned-environment test caught that API detail.
Key functions: `build_graph`, `execute`, `validate_role`, typed `Tools.call`.
Demo: `scripts/demo.py --mode multi`, then inspect Activity and Gap review. Restart
worker between steps and reopen the run; integration tests exercise checkpoint logic
when a real test database is supplied. The unit restart test uses a memory saver and
is explicitly not evidence of Postgres persistence.
Q: Why five roles but six model calls? A: lead researcher plans and later synthesizes
candidates; the other four roles each have a task. Q: Why not parallel everything? A:
review needs candidates and experiments need review. Q: Why require objections to cite
sources? A: unsupported skepticism is not a valid contradiction either.

## 5 — product, evaluation and handoff
Flow: polling persisted API data → status/trace/matrix/review → PDF.js page/region viewer
→ Markdown download; demo mode loads only static JSON/source PDFs. Escape closes the
evidence dialog; focus is trapped/restored and narrow screens preserve navigation.
Key modules: React App, PdfPreview, `rgi.evaluate`, `scripts/measure_pipeline.py`.
Demo: `cd frontend && npm run demo`, inspect original page, download report, reload.
Then `uv run python -m rgi.evaluate --offline`; read provenance before metric values.
Q: How compare architectures fairly? A: frozen corpus/model and shared declared budget,
actual usage exposed, draft relevance labels reviewed by humans, denominators explicit.
Q: What if multi-agent performs worse? A: report it; inspect retrieval coverage, budget
and reviewer failures. Q: What does null support mean? A: no human-scored denominator,
not zero accuracy and not perfect support. Q: Can the public demo run research? A: static
mode cannot; private local mode can, with configured provider and worker.

Generated implementation is for learning/review; do not claim personal authorship of
all generated work. Work through functions, deliberately break invariants, rerun tests,
and explain the observed failures before using this project in an interview.
