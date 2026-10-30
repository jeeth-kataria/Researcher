# Implementation and verification status

Current architecture follows the user-approved SQLite + Groq amendment (ADR 004).
The five original milestones remain organized by behavior rather than the retired DB.

| Milestone | Implemented | Verification |
|---|---|---|
| Foundation | SQLite schema/version/init, WAL, config, health, jobs, heartbeat, pinned locks | File-backed integration, atomic claim race, fresh-process read, OS lock/death release |
| Evidence | Immutable ingest, CPU parser/embedding paths, FTS5/exact cosine RRF, PDF inspector | Real synthetic PDF bytes through pypdf and actual SQLite retrieval; Docling/BGE assets remain pending |
| Baselines | RAG and single researcher, typed tools/outputs, provider adapter, durable report/budget | Fixture controls plus official Groq/Gemini SDK mock HTTP contracts; live keys absent |
| Multi-role | Five personas/six bounded model stages, review/experiments, SqliteSaver, cancel/resume | Real on-disk checkpoints, worker restart, lease recovery, quota/ambiguity controls |
| Product | Neumorphic orchestration UI, static example, browser stack, evaluations and learning docs | Build/static browser and local integration results recorded in VERIFICATION.md |

No live-provider quality, successful Docling/BGE ingestion, real-paper capacity estimate,
always-on hosted worker or scientific novelty is claimed. Public static deployment has
not been requested/executed. Optional remote live-job transport, discovery/reranking and
human relevance/support annotations are separate work. Original fixture outputs and
prior parser measurements remain labeled, not relabeled as SQLite/real-LLM benchmarks.
