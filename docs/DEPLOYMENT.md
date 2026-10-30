# Zero-required-cost deployment modes

Nothing was externally deployed. Local and static modes require no cloud accounts.
Official plan/connection documentation was checked 2026-10-30; check the actual account
again before deployment. A service asking for a card or upgrade is not a dependency:
use local mode or the static export instead. Never create artificial keepalive traffic.

## Recommended release sequence for Researcher

1. **Public showcase first.** Import `jeeth-kataria/Researcher` into a personal Vercel
   Hobby project with root directory `frontend`, framework Vite, install `npm ci`, build
   `npm run build -- --mode demo`, output `dist`. `frontend/vercel.json` already specifies
   the demo build and security headers. No environment variables, database, API, model
   credentials, domain purchase or laptop connection are needed for this release.
   Keep the project on Hobby and check account eligibility/limits; do not add a paid
   service. This document is a plan; no Vercel deployment has been created.
2. **Let visitors inspect the process.** Orchestration is the opening panel. Six saved
   stages represent five personas in multi-agent mode: the lead appears twice. Stage
   selection shows summaries, recorded timing when available, and links to related
   final-artifact sources. Visitors can step through the original synthetic event
   records, review a contradicted candidate, open a PDF and download the report. No
   background LLM work starts when a visitor loads or explores the showcase. Walkthrough
   progress is presentation state, not backend run state. The provider/provenance
   disclosure remains visible. PDF.js is downloaded only when a source is opened.
3. **Verify the private research workspace.** Start PostgreSQL/pgvector, download pinned
   model assets, run the seven database integration tests and the opt-in local browser
   flow, then perform one explicit Gemini run with a verified free-tier account. Check
   every claim and candidate against papers. A reviewed, publishable real-run replay
   would be a separate export/loader addition; the current showcase stays synthetic.
4. **Gate live public investigations.** Optional mode C below needs shared private PDF
   storage, scoped auth, rate/admission limits, a measured query-embedding path and
   tested outbound laptop job claiming before visitors can submit work. A laptop that
   is off cannot process jobs. The UI must expose queued/offline/quota-paused states.
   Start with owner-only live submissions; public read-only viewing is the safe initial
   scope for the shared quota. Always-on public research is not promised under ₹0.

After an explicit deployment request, use a preview deployment first and verify the
public URL: fixture label, stage map, walkthrough, source/PDF loading, Markdown export,
mobile width and absence of API requests/credentials. Then promote the same reviewed
static build. Connecting this GitHub repository for automatic deployments would make
later pushes to the configured production branch publish automatically; choose that
setting deliberately. Save the prior deployment so a rollback is available.

## A — local application
Use README / LOCAL_SETUP. Original PDFs and artifacts are on local disk; PostgreSQL
holds durable records/vectors/checkpoints. Existing laptop runs CPU ingestion and
research worker. No assumed GPU/RAM capacity or always-on availability. Keep the local
API bound to loopback. Back up both database and source files before changes.

## B — static read-only portfolio example
`cd frontend && npm ci && npm run build -- --mode demo`. `dist` can be served by any
static server, without a backend, key or laptop worker. The checked-in sample consists
only of original synthetic PDFs, report and JSON. It labels fixture provenance on the
page and in exports. Buttons cannot create uploads/runs. Returning to local workspace
only tries a same-origin `/api` path; no HTTPS-to-localhost assumption is made.

`frontend/vercel.json` prepares a static demo build. Set the Vercel project root to
`frontend`, choose **Hobby**, and verify account eligibility/usage before publishing.
Hobby is intended for personal/non-commercial use; do not infer eligibility for a
commercial service. Inspect current included usage and behavior at limits in the
[Vercel Hobby docs](https://vercel.com/docs/plans/hobby). No automatic upgrade is needed
for this repository. Publishing requires a separate explicit user request.

Export a private completed run with `uv run python scripts/export_run.py RUN_UUID`.
This copies report/source text/JSON, not PDF bytes or credentials. Review licenses and
privacy before putting third-party passages or PDFs in public assets. The bundled demo
loader is intentionally a synthetic example, not an unreviewed real-run publishing tool.

## C — optional hosted API/database + laptop worker (not enabled)

Prepared API image: `docker build -f deploy/Dockerfile.api .`. It installs core API
packages only, no Docling/SentenceTransformers/weights. It has **not been built or memory
sized here** because the Docker daemon is unavailable. Current local retrieval encodes
queries using BGE in the API. Therefore a slim hosted API needs an additional measured
query-embedding design before live search can work without worker extras. Do not claim
the current API fits a small free instance or that this optional mode is production ready.

Potential services and constraints, from current official docs:

- [Render Free](https://render.com/docs/free): free web services sleep after idle time,
  have ephemeral filesystems and shared monthly usage limits. Store neither PDFs nor
  durable state there. Free Render Postgres is not the durable DB choice here; check
  its expiration/backup limits. The heavy worker stays on the laptop. Keep owner writes
  disabled until server-side authentication, source storage and limits are verified.
- [Supabase Free](https://supabase.com/pricing): current advertised allowances include
  500 MB database, 1 GB file storage, and projects pausing after a week of inactivity.
  These are small bounds for vectors and checkpoints, not a permanent capacity promise.
  Do not enable paid overage/compute. Manually restore paused projects when needed.
- [Supabase connections](https://supabase.com/docs/guides/database/connecting-to-postgres):
  prefer a direct connection if the laptop supports its IP family, otherwise a session
  pooler on the supported port. Transaction pooling is unsupported: graph execution uses session advisory locks
  as well as checkpoints. Session affinity is required. Use TLS and test
  actual migration/checkpoint/lease semantics against the chosen connection. Never use
  privileged database credentials in the browser.

Before enabling C, implement/verify the optional object-storage adapter and private
storage policies, least-privilege SQL/checkpoint roles, server-verified owner auth,
explicit CORS origin, measured API memory including query handling, secure laptop
connection and restore/backup process. Existing local disk adapter cannot magically
share laptop files with an ephemeral hosted API. These are documented limits, not
working features. No laptop port forwarding or public laptop endpoint is needed:
the worker would claim database jobs outbound. Offline laptop means queued hosted jobs
remain queued and the real heartbeat says offline.

Hugging Face hosted compute is not offered as a required fallback. Account-plan creation
eligibility was not verified, so no free Docker/Gradio hosting promise is made. No cloud
account or external deployment is required to finish local/static implementation.
