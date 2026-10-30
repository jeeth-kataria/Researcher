# Codex build prompt: Research Gap Investigator

You are my senior engineering partner and teacher. Build this project from scratch in this workspace. Implement and verify working software, not just a proposal or mock interface. I want to understand and defend every important decision in interviews.

## Product and owner context

I am Jeeth, a Computer Science student graduating in 2027. Python is my strongest language. I have built a PDF RAG application and want a substantial engineering upgrade: inspectable evidence, reliable agents, resumable execution, evaluation, and a polished interface. Build incrementally so I understand the foundations before the multi-agent layer.

Product name: Research Gap Investigator.

User promise: Give the application a focused research question and a collection of papers. It compares what the papers demonstrate, identifies uncertainties and candidate gaps, tries to disprove those gaps, and proposes falsifiable experiments. Every literature-based factual claim must have inspectable supporting evidence or be explicitly marked unsupported.

Start with English, digitally generated PDFs and a narrow corpus about agent memory and long-context reliability. Domain selection must remain configurable. Do not assert that a real research gap exists in this area before investigating it.

The deliverable is a personal portfolio application and a reproducible local engineering project. A candidate gap is not a proven novel scientific discovery. Never promise guaranteed publication, automated scientific truth, or guaranteed exhaustive coverage.

## Nonnegotiable cost and scope constraints

- Required spending is INR 0. No paid APIs, paid hosting, paid subscriptions, credit-card setup, time-limited promotional credits, or automatic upgrades as dependencies.
- Use existing laptop compute for parsing, embedding, and the research worker. Do not assume a GPU or a specific RAM capacity. Inspect the environment and provide a CPU path; document measured resource needs.
- Use free-tier Gemini through Google AI Studio when I supply a key. Keep billing disabled. Check current official availability and account quotas rather than hardcoding obsolete limits.
- Local development must not depend on Supabase, Render, Vercel, or a hosted LLM account. Provide local PostgreSQL and clearly labeled fixture-based offline smoke tests. Offline fixtures are not real research results.
- Optional local LLM inference through Ollama may be added behind the same interface after the main path works. Do not download a large generative model automatically or promise equal quality.
- Never silently switch to a paid provider, another model, or another account when a quota is exhausted. Pause and resume the run, or require an explicit configured provider choice.
- Do not rotate accounts or API keys, generate artificial keepalive traffic, or otherwise evade provider limits.
- Build the local application first. Prepare free deployment configuration and instructions afterward. Deploy externally only if I request it and the available environment supports it.
- No Kubernetes, microservices, Redis, Celery, paid search APIs, graph database, fine-tuning, autonomous code execution, or GPU dependency in version one.
- Research experiments are proposed, not executed automatically. Their execution is a later product extension.

## Agreed technology stack and decision rationale

Preserve these choices unless you discover a concrete incompatibility. Record necessary changes and reasons in architecture decision records. Verify current APIs and compatible stable versions in official docs; pin dependencies and commit lockfiles. Do not install arbitrary newest versions without checking compatibility.

1. Frontend: React, TypeScript, Vite, Tailwind CSS. This is an interactive workspace with a Python backend; server rendering and SEO are not central. Prefer this to Next.js for less server-side duplication, and to Streamlit/Gradio for control over evidence panels, run history, and document navigation. A small component library and PDF.js-based viewer are acceptable if useful and compatible.
2. Backend: Python, FastAPI, Pydantic. Keep parsing, embeddings, agents, and APIs in Python. Prefer this to Node.js to avoid a second backend language, Flask for built-in typed validation/API contracts, and Django because we do not need an admin-heavy full-stack framework. Async HTTP does not make CPU-bound parsing nonblocking: use a separate worker process.
3. Orchestration: open-source LangGraph running locally, with PostgreSQL-backed checkpoints. First implement retrieval and a single-agent loop as understandable Python functions. Then wrap these in explicit graph nodes. Prefer explicit state, bounded transitions, and recoverable execution over unconstrained agent conversation. Do not require LangSmith or managed agent hosting.
4. PDF ingestion: local Docling with structure-aware, tokenizer-aware chunking. Preserve headings, captions, tables where supported, and original source locations. Compare against a lightweight text-extraction baseline on a few PDFs. Do not assume parsing is flawless or add a paid parser.
5. Embeddings: local BAAI/bge-small-en-v1.5 initially, using a suitable local inference library. It uses 384-dimensional vectors and a limited input window; verify the model card and enforce its tokenizer limits including headings, instructions, and special tokens. Prefer compact CPU inference and no API quota. Record model revision and preprocessing version. Do not silently truncate long chunks or mix embeddings from different models in one index.
6. Database: PostgreSQL plus pgvector. Store relational research data and vectors together. Prefer one database to FAISS plus a separate metadata database, or adding Qdrant/Pinecone solely for the initial small corpus. Use SQLAlchemy and Alembic where they improve clarity. Never use SQLite as a hidden substitute for PostgreSQL retrieval in integration tests.
7. Retrieval: PostgreSQL full-text search plus vector similarity, combined with reciprocal rank fusion. This supports exact names and semantic queries. Begin with exact vector search; add HNSW only after measurements justify it. Cross-encoder reranking is an optional evaluated improvement, not a required initial dependency. Postgres full-text ranking is not BM25; describe it accurately.
8. LLM: configurable Gemini API provider, initially gemini-2.5-flash only if its current free access is verified. If unavailable, identify an actually available free model and document the change before using it. Prefer one model for all agent roles initially; compare alternatives with evidence later. Use the official SDK and validated structured responses where supported.
9. Execution: one Python worker initially, PostgreSQL job records, leases/heartbeats, bounded retries, idempotent ingestion, and persistent run state. Graph checkpoints track progress inside a run; jobs track dispatch and worker ownership. No Redis/Celery until throughput demonstrates a need.
10. Storage: local disk adapter by default, optional Supabase Storage adapter. PDFs belong in file/object storage, not database blobs. Database holds metadata and artifact references. Keep vectors, SQL records, PDF bytes, parsed artifacts, caches, and graph checkpoints conceptually distinct.
11. Hosting: optional Vercel Hobby for the static frontend, Supabase Free for hosted Postgres/pgvector and selected example PDFs, optional Render Free for a lightweight API only. The heavy worker stays on the laptop. Do not assume Hugging Face Docker/Gradio compute creation is free: recheck current account-plan requirements. Recheck every proposed service's official limits before publishing deployment instructions. A static example-report demo is a valid zero-cost fallback.
12. Development: a simple monorepo, uv or another justified reproducible Python environment manager, npm with a lockfile, Docker Compose for local PostgreSQL/pgvector, pytest for backend tests, and Playwright for a few meaningful end-to-end flows. Native local PostgreSQL setup should be documented for users without Docker. Avoid making a paid desktop container subscription necessary.

Document for each significant choice: requirement, chosen option, alternatives, tradeoff, and what evidence would make us change it. Do not claim these tools are universally superior.

## Project organization and teaching requirements

Inspect the existing workspace and any applicable instructions first. Preserve unrelated work. If empty, create a clean monorepo with frontend, backend/worker, migrations, tests, fixtures, and docs. Choose a simple consistent layout rather than many tiny packages.

Create a root README, .env.example, architecture documentation, decision records, a build progress document, and an interview guide. Keep a repository-level project brief with the stable requirements so future Codex turns retain context. Do not create conflicting or unnecessarily broad agent instructions.

Explain important steps briefly as you work: what changes, why, how to verify, and the main tradeoff. Use docstrings and comments for non-obvious logic. At the end of each milestone, update a learning guide with request/data flow, key functions, a runnable demonstration, and a few interview questions with accurate answers. Do not pretend I personally implemented work you generated; help me learn and review it.

## Data and evidence model

Design migrations with foreign keys, ownership where relevant, timestamps, indexes, and suitable uniqueness constraints. Core concepts should include:

- Collections and research questions/scope.
- Papers, metadata, source URLs, document versions, content hashes, parsing status and quality warnings.
- Passages/chunks with stable IDs, text, document version, heading, page references, parsed-document item IDs, and bounding boxes when available.
- Embedding model/revision and preprocessing identity.
- Per-paper structured methods, datasets, baselines, metrics, experimental conditions, results, and author-stated limitations, linked to evidence.
- Research runs with frozen corpus/version manifest, model/configuration/prompt versions, budgets, status, and timestamps.
- Jobs, worker leases, cancellation requests, resumable states, and errors.
- Agent steps, tool calls, tool results, durations, token usage when available, and evidence IDs.
- Claims, evidence links, candidate gaps, counterevidence, review decisions, experiment proposals, and reports.

Retain content hashes and provenance across reingestion. Treat a new paper version as a new version rather than silently overwriting the evidence supporting existing reports. Avoid duplicate embedding work when the document and processing configuration are unchanged. Invalidate caches when relevant versions change.

## Ingestion and retrieval behavior

1. Accept bounded PDF uploads; show validation and ingestion progress.
2. Store original bytes, hash the content, parse in the worker, and preserve provenance. Disable expensive OCR by default for embedded-text PDFs. Detect and explain insufficient text or unsupported scans.
3. Generate structure-aware chunks within the embedding model's token limit. Handle headings and tables without silently losing context. Document chosen chunk parameters as initial hypotheses to evaluate, not universal best values.
4. Generate embeddings locally in bounded batches and store searchable records transactionally.
5. Expose a retrieval inspector showing keyword rank, vector rank, fused rank, paper identity, source passage, and surrounding context. Do not display ranking scores as calibrated confidence probabilities.
6. Deduplicate results and provide configurable paper diversity. Preserve the ability to retrieve neighboring passages or a full relevant section when short passages are insufficient.
7. A failed PDF must not prevent the rest of a collection from ingesting. Show partial failures honestly.

Version one uses uploaded papers. A later milestone may add user-confirmed discovery from the official arXiv API with documented rate limits, caching, deduplication, and open-access downloads. Do not scrape Google Scholar. Distinguish abstracts from full text. A corpus-only run must state that its prior-work coverage is limited to that corpus; a search returning no hits does not prove novelty.

## Agent design: one orchestrator plus four workers

There are five roles, not four total:

1. Lead researcher/orchestrator: refine scope, make a bounded plan, delegate investigations, request targeted follow-ups, and synthesize the final report. State what can and cannot be concluded from the corpus.
2. Literature investigator: assess collection coverage, find relevant documents/passages, and record inclusion/exclusion decisions and searched queries. External discovery is optional and explicitly identified.
3. Methods analyst: extract comparable methods, datasets, baselines, evaluation conditions, metrics, limitations, and evidence. Missing values remain unknown. Do not compare numbers as like-for-like when experimental conditions differ.
4. Skeptical reviewer: attempt to invalidate each proposed gap using prior work, counterexamples, contradictions, and missing context. Apparent disagreement may result from different settings. Require supporting evidence for objections too.
5. Experiment designer: turn surviving candidate gaps into falsifiable hypotheses with baselines, variables, dataset needs, metrics, resource estimates, failure criteria, and feasibility limits. Label ideas as proposals rather than established facts.

The orchestrator can propose candidate gaps after evidence extraction. The reviewer challenges those candidates before the experiment designer works on surviving ones. Some retrieval/extraction work can overlap, but do not run dependent steps in parallel merely for animation. Cap LLM concurrency independently of role count, initially at one configurable call at a time.

Give agents a small typed tool set, such as search_passages, read_context, inspect_paper, list_corpus, record_claim, fetch_extraction, and submit_review. Each tool validates inputs, enforces collection scope and budgets, and returns structured results with evidence IDs. Agents may choose bounded follow-up queries. Keep deterministic validation in code. No arbitrary shell, browser, network, filesystem, or code execution tools for these agents.

Build explicit graph states and typed outputs. Bound the number of tools, steps, retries, and revision rounds. Agents can abstain or request evidence; they must not invent citations to satisfy an output schema. Persist concise evidence-backed findings and operational traces, not private chain-of-thought.

## Claims, gap validity, and reports

Every literature-based factual claim needs exact evidence references. Validate that citations exist, belong to the run's allowed document versions, and that quoted text maps to the stored source. Citation existence and string matching do not establish semantic support: include an evidence-support review and evaluate it separately. Do not claim an independent LLM reviewer guarantees correctness.

Separate:
- Author-stated limitations.
- An observed coverage hole within the inspected corpus.
- A proposed hypothesis or inference.
- A candidate gap that survived the configured review.
- A candidate contradicted by prior work.
- An unresolved question with insufficient evidence.

Do not present an absolute novelty verdict. Agent agreement is not independent scientific verification. Do not manufacture percentage confidence scores. Show evidence, corpus/search scope, missing information, objections, and reasons for the review status.

Each candidate gap should include: scoped description, significance, evidence, search/coverage record, strongest counterevidence, unresolved concerns, reviewer disposition and rationale, and a proposed experiment if appropriate. Experiments should include what result would refute the hypothesis. Hardware-dependent experiments must state their requirements; never assume access to robot arms or expensive GPUs.

Generate an exportable Markdown report containing scope/corpus manifest, literature matrix, supported findings, rejected and surviving candidate gaps, counterevidence, experiment proposals, limitations, and references. No need for PDF export in the first version.

## Application interface

Create a polished, focused dark interface with restrained red accents, readable text, accessible contrast, keyboard access, and clear loading/error/empty states. Avoid decorative agent chat bubbles and fake research activity.

Core screens:
- Collection library with upload, document status, versions, and failures.
- Research setup with question, scope, collection, and editable budget limits.
- Run view with real step status, concise findings, tool/evidence activity, worker availability, cancellation, and quota state.
- Literature comparison matrix with evidence links and unknown values.
- Gap review view with supporting evidence, counterevidence, and proposed experiments.
- Evidence viewer that opens the correct paper/page and highlights source regions when coordinates are available. If extraction coordinates are unavailable, show page and exact text with an honest fallback; do not invent bounding boxes.
- Run history and report export.
- Public example reports with clearly labeled provenance and read-only behavior.

Polling persisted run events is sufficient initially. Add SSE only if justified; reconnection must preserve progress either way. Never require a long-lived browser connection for the worker to continue.

## Reliability and no-spend controls

- Submit research as a job and return immediately with a run ID. Do not put the entire workflow inside a request handler or unpersisted FastAPI BackgroundTasks.
- Use atomic job claims with ownership leases. Recover abandoned work after a lease expires. Expect at-least-once execution and make writes idempotent; do not claim exactly-once external LLM calls.
- Persist results and checkpoints. Restarting an API, worker, or browser must not silently erase runs. Handle the crash window around external model calls explicitly; a cached result cannot prevent every duplicate call.
- Respect provider retry-after information and use bounded backoff. Persist waiting-for-quota status. Exhausted daily limits pause work instead of retrying indefinitely.
- Use configurable collection/upload limits, run token/call budgets, output limits, tool limits, and review-round limits. Propose conservative defaults; distinguish application limits from provider quotas.
- Cache valid structured extractions by document hash, parser/chunker version where relevant, model, prompt/schema version, and relevant settings.
- Support cancellation between steps. A currently running provider request may have to finish; explain that limitation.
- Record token usage when supplied by the provider and show unknown when unavailable. Do not fabricate latency, cost, or benchmark statistics. Free-plan usage is still quota consumption.
- Worker heartbeat must represent a real worker, not just a healthy API. If it is offline, new hosted jobs stay queued and the UI says so.

## Security and public demo boundaries

Default local API binding is loopback. Use explicit CORS configuration. Keep API keys and privileged database credentials exclusively server-side; never put them in VITE-prefixed variables or Git. Include sanitized environment templates and safe logging.

Treat PDF text as untrusted data. Instructions found inside papers cannot change agent tools, budgets, or system behavior. Validate generated tool calls in code. Reject path traversal, oversized files, wrong file types, and cross-collection evidence references. If adding URL import, block private/internal network addresses and unsafe redirects and limit downloads.

The public demo is read-only by default. Enable research creation/upload only with an explicit owner-authenticated mode and enforced limits. If using Supabase Auth, verify tokens server-side and enforce authorization; do not add an insecure client-side admin flag. Apply appropriate storage access policies. Avoid exposing raw prompts with secrets in traces.

Do not redistribute third-party PDFs in a public demo unless their license permits it. Use small original synthetic fixtures for deterministic tests and lawful open-access examples where available. Clearly label synthetic data, generated sample reports, and recorded real runs. Do not fake a live research report in response to a real request.

## Zero-cost deployment modes

Mode A: complete local app with local PostgreSQL, local files, local API and worker; optional free LLM key. Provide reproducible startup commands and health checks.

Mode B: static hosted frontend with exported, inspectable example reports and citations. Usable without a live backend, keys, or a laptop online. Clearly label it as example exploration, not live generation.

Mode C: optional Vercel frontend, lightweight Render API, Supabase database/storage, and laptop worker. The worker claims hosted jobs from the database through a secure supported connection, using least privilege where practical. Do not expose the laptop directly or assume an HTTPS public frontend can call localhost. Verify current pooler/direct connection compatibility and choose checkpoint/connection settings accordingly. Keep heavyweight parser/model dependencies out of the slim hosted API image. Measure the API's memory use before claiming it fits a free instance.

Cloud free tiers can sleep, pause, or change. Keep durable state out of ephemeral hosting filesystems. Document quotas, cold starts, manual restore, backup/export, and the offline-worker limitation honestly. No cloud account creation is required to finish Mode A and B. Do not claim an always-on free worker.

## Meaningful validation

Use pytest, real local PostgreSQL/pgvector integration tests, and a few browser tests. Mock external LLM responses only for deterministic tests and label those runs. Keep real provider tests opt-in; never burn quota in the default suite.

Important cases:
- Duplicate ingestion, version changes, and cache invalidation.
- Chunk token limits and preserved provenance.
- Retrieval restricted to the selected collection/document versions.
- Known relevant passages returned for a small labeled retrieval set.
- Malformed structured output, invalid evidence IDs, and unsupported claims.
- A previously studied topic offered as a supposed gap is rejected or marked uncertain when counterevidence is present.
- Corpus-only absence is not turned into universal novelty.
- Job claim races, cancellation, worker restart, and checkpoint resumption.
- Provider throttling and exhausted quota without a paid fallback.
- Read-only demo access, secret handling, and untrusted document instructions.
- Browser flow: ingest fixture, inspect retrieval, run deterministic research fixture, open evidence, export report, reload saved run.

Build an evaluation harness comparing: ordinary RAG, one research agent, and the multi-agent workflow on the same frozen corpus and model. Report resource budgets and actual usage; use comparable budgets where feasible and expose differences. Measure retrieval recall@k, factual claim support, citation correctness, false candidate-gap claims on known controls, latency, and tokens. Explain denominators and how judgments were made. Agent self-scores are not ground truth. Create a small draft evaluation set and mark it pending human review until actually reviewed; never label model-generated annotations human-validated.

Publish measured results only after running the evaluation. Multi-agent superiority is a question to test, not a predetermined acceptance condition. If the baseline performs better, report it and investigate.

## Implementation milestones

Work sequentially and keep the application runnable after each milestone. Do not stop after planning, scaffolding, or a frontend shell. Resolve routine implementation decisions yourself and continue without repeated confirmation. Ask only for genuinely blocking information or explicitly gated actions. Missing API credentials must not stop unrelated local implementation, deterministic tests, or the example explorer.

1. Foundation: inspect workspace; record brief/ADRs; set up environments, database migrations, local services, configuration, and minimal UI/API/worker health checks.
2. Evidence pipeline: upload and store PDFs, parse, chunk, embed, retrieve, and inspect citations. Demonstrate this before adding multiple agents.
3. Single-agent baseline: typed tools, validated outputs, report generation, persisted runs, quotas, and a reproducible example.
4. Multi-agent research: implement the five roles with bounded LangGraph execution, skeptical review, experiment proposals, checkpoints, and cancellation.
5. Product completion: integrated frontend, evidence navigation, matrix, gap review, report export, meaningful tests/evaluations, static demo export, optional hosting configuration, and clear learning/interview documentation.

At each milestone, run appropriate checks, fix failures, update progress and docs, and continue. Do not expand scope into unrelated features. Keep optional improvements out of the critical path.

## Completion criteria and final handoff

The core is complete when a fresh checkout can start the local database/API/worker/frontend using documented commands, ingest a real supported PDF, retrieve source-linked passages, execute a real provider-backed run when a free key is configured, and inspect/report results without paid dependencies. Restart behavior, evidence validation, quota behavior, and read-only public mode must be demonstrated. Deterministic offline fixture mode and static example exploration must work without a key, with prominent labels.

If real provider execution, third-party downloads, browser tooling, or deployment cannot be tested in the available environment, state exactly what was implemented, what ran, and what remains unverified. Do not present fixture-based validation as a live LLM success.

Finish with: what works; exact setup/run/test/demo commands; environment variables I must supply; test/evaluation results; unresolved limits; and a concise walkthrough of ingestion, retrieval, job execution, graph state, evidence checking, and report generation. Include an accurate proposed resume bullet without invented metrics, plus interview questions based on the actual implementation.

Start now by inspecting the workspace, briefly explaining your implementation sequence, recording the project brief, and implementing milestone one. Continue toward the complete project rather than returning only a plan.
