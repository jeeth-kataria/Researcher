# Interview guide based on this implementation

A defensible description: “I studied and extended a local research workbench generated
with Codex. Its engineering focus is inspectable evidence and recoverable execution,
not an automated novelty oracle.” Review actual code before claiming implementation
ownership. No benchmark/novelty/accuracy metric belongs on a resume until evaluated.

1. **What does a run freeze?** Ready document-version IDs, hashes, processing/model
   identity, question/scope and prompt/schema/budget config. Budget resume changes are
   explicitly audited; prior source evidence stays immutable.
2. **What is the database buying you?** Relational constraints, atomic job dispatch,
   FTS, exact vector search and graph state in one locally operated service. This is
   simpler for this corpus than separate queues/vector stores, not universally optimal.
3. **Why not just RAG?** RAG is implemented as a baseline. Extra stages separate
   extraction, candidate generation, objections and proposals. Whether they improve
   outcomes is an evaluation question with matched corpus/model and visible usage.
4. **What prevents hallucinated citations?** IDs must come from retrieved in-manifest
   passages; normalized quotes must match. This prevents provenance fabrication, not
   misleading interpretation. Separate support review and human evaluation remain.
5. **How are job races handled?** SKIP LOCKED atomic claims, ownership/expiry leases,
   heartbeat renewal, fenced writes. Dispatch remains at least once. Integration tests
   need real PostgreSQL, not SQLite or a mock pretending to prove locking semantics.
6. **What happens at a crash?** Completed node checkpoint resumes; cached completed
   model response prevents some repeats. Pending external call outcome is ambiguous;
   pause and explicitly acknowledge potential duplicate quota use before resending.
7. **Is full-text rank BM25?** No. Postgres `ts_rank_cd` is its own FTS ranking, fused
   with vector rank via RRF. Scores are not calibrated confidence probabilities.
8. **What is the embedding boundary?** BGE-small, 384 dimensions, fixed model revision
   and preprocessing; actual tokenizer bounds include heading/special/query-prefix
   tokens. No silent truncation; fixture hashes cannot enter real Gemini research.
9. **How are PDFs handled safely?** Bounded bytes/pages, signature check, generated
   content-addressed storage keys, local OCR-off parser, untrusted source text, no
   arbitrary execution tools. Source coordinates are preserved when available.
10. **What is actually free?** Local compute/software and static example. Optional Gemini
    requires an actually free-tier account with billing disabled; the app does not
    verify billing from a key. Hosted quotas/sleep/pausing can change. No always-on free
    worker claim, no paid fallback or key rotation.
11. **What has been verified?** Consult VERIFICATION.md for current counts and limits.
    Mock-transport SDK tests are not live provider success; memory checkpoint tests are
    not PostgreSQL durability; static browser flows are not full ingestion integration.
12. **What would you change first with evidence?** Run real PostgreSQL restart/race tests,
    Docling/BGE measurements and human-reviewed evaluations; improve chunking/tool
    autonomy only in response to observed failures. Do not add distributed infrastructure
    solely to make the architecture diagram look sophisticated.

Proposed resume bullet: “Built an evidence-first research workbench using FastAPI,
PostgreSQL/pgvector, local PDF processing, hybrid retrieval and bounded LangGraph
workflows, with citation validation, a React evidence inspector and deterministic tests.”
Use “reviewed/extended” in place of “built” until it accurately describes your work.
