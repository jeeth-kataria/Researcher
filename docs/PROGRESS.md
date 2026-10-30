# Build progress and verification gates

All five implementation milestones have code, documentation and runnable commands.
The core is **not certified end-to-end in this sandbox**; the separate evidence below
prevents fixture/browser success from being mistaken for live research verification.

| Milestone | Implemented | Demonstrated here | Remaining verification |
|---|---|---|---|
| 1 Foundation | Monorepo, pinned locks, config, migration, Compose, health, real heartbeat, jobs | Dependency install, imports, health/security unit tests | PostgreSQL startup/migration on permitted host |
| 2 Evidence | Upload/storage/hash/versioning, Docling + pypdf, token chunks, BGE CPU, hybrid FTS/vector, inspector/PDF viewer | Three actual synthetic PDFs parsed by pypdf, provenance/chunk checks, browser PDF rendering | Docling assets blocked by model-download DNS; BGE model load and pgvector retrieval pending |
| 3 Baselines | RAG and single researcher, typed tools/output, evidence validation, durable run records, reports/budgets/quota | Deterministic outputs; official Gemini SDK mock HTTP success/429 contracts | Real Gemini key/account quotas and actual research quality |
| 4 Multi-role | Five roles, bounded graph, skeptical review, experiments after review, PostgresSaver, cancellation/recovery/ambiguity | Pinned LangGraph unit resume test; false candidate fixture challenged; no model fallback | Real Postgres restart/race/lease/quota integration tests |
| 5 Product | Integrated dark React interface, matrix/review/evidence/history/export, static demo, evaluation/profiling, docs | Production builds, two Chromium example flows including mobile, fixture evaluation measurements | Full ingestion browser flow, human relevance/support/gap labels, optional hosting |

Sequence: foundation → evidence functions → baseline → graph → integrated product.
Milestone teaching notes are in LEARNING_GUIDE.md; decision rationale is in adr/.

No real research gap, exhaustive coverage, independent scientific verification, live
Gemini success, always-on free worker, cloud deployment, or multi-agent superiority is
claimed. No external account was created, no paid service configured, no API key used.
Optional arXiv discovery, Ollama, reranking, Supabase adapter/auth and full Mode C are
explicitly deferred. Local mode and backend-free static examples are the version-one
paths; README identifies actual environment limitations.
