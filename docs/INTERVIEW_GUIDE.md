# Interview ownership guide

This project was generated with Codex assistance. Review, run and explain the paths you
claim ownership of. Current architecture is SQLite/Groq; ADR 004 records the amendment.

1. **What does it do?** Investigates a bounded uploaded corpus, challenges provisional
   gaps and proposes falsifiable experiments with source passages. It cannot certify novelty.
2. **Why SQLite?** One local file removes a database-server dependency for a single-laptop
   workflow. FTS5, vectors, relational data and checkpoints share a durability boundary.
3. **What is the concurrency tradeoff?** WAL allows concurrent readers, but writes serialize.
   Short BEGIN IMMEDIATE transactions make claim/count/update sequences atomic. One worker
   is the supported configuration; cross-host SQLite sharing is not supported.
4. **Why a separate worker?** Parsing/embedding/model calls outlive HTTP requests. Durable
   jobs, heartbeat, lease and cancellation survive closing a tab or restarting the API.
5. **Why both leases and an OS lock?** Leases/fences protect application writes. Checkpoint
   writes occur after a node returns; a per-run flock covers graph invocation through those
   commits and releases automatically on process death.
6. **Is it exactly-once LLM execution?** No. The response can be lost after a remote call
   succeeds. A persisted pending/uncertain intent pauses and requires explicit duplicate-
   quota acknowledgement. Caching cannot erase this ambiguity.
7. **How is retrieval ranked?** SQLite FTS5 BM25 and exact 384D cosine ranks combine via
   RRF, then source deduplication/diversity. This is genuinely BM25, unlike the superseded
   Postgres ts_rank_cd path. Scores are not calibrated scientific confidence.
8. **Why Groq?** User selected it as the primary API. Official SDK, allowlisted structured-
   output models and account-specific free quotas. Keys remain server-side. Gemini is
   secondary; fixtures are explicit and never silently substituted for real research.
9. **What do agents add?** A bounded sequence of specialist roles with explicit artifacts,
   counter-search, skeptical review and proposals only after review. One lead appears
   twice. No claim of parallel autonomous workers or measured multi-agent superiority.
10. **How do you validate citations?** Exact normalized quotes, retrieved passage IDs,
    frozen manifest membership, same-paper matrix references and separate support review.
    These structural checks are necessary but human semantic review is still needed.
11. **What has actually been tested?** See VERIFICATION.md for current counts: actual file-
    backed SQLite integration and explicitly synthetic browser/provider controls. Mock SDK
    transport tests are not live Groq/Gemini calls; fixture vectors are not BGE benchmarks.
12. **What is deployable now?** Read-only synthetic static explorer, plus private local
    research. A separate hosted API cannot directly share laptop SQLite; live public jobs
    need a new remote coordination/storage design and verified auth/limits.

Possible resume wording, after personally verifying the claimed paths:

> Built a local evidence-first research workbench with FastAPI, SQLite FTS5, hybrid
> retrieval, a separate durable worker and bounded LangGraph orchestration; added
> source-linked review, recoverable quota controls and an inspectable agent workflow.

Discuss assistance candidly; do not claim validated scientific novelty, production
hosting, live model accuracy, or unperformed scalability benchmarks.
