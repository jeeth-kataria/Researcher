# ₹0 deployment plan — static public showcase + local research

Nothing has been externally deployed. SQLite/Groq are the current architecture, accepted
in ADR 004. Required spend remains ₹0. No card, paid service, hosted worker or custom
domain is required. Check actual account terms/usage before publishing.

## Public showcase

Import `jeeth-kataria/Researcher` into an eligible Vercel Hobby project:

| Setting | Value |
|---|---|
| Root | `frontend` |
| Framework | Vite |
| Install | `npm ci` |
| Build | `npm run build -- --mode demo` |
| Output | `dist` |
| Environment variables | None |

`frontend/vercel.json` specifies the demo build and security headers. Hobby is intended
for personal/non-commercial projects; verify eligibility in the
[official plan documentation](https://vercel.com/docs/plans/hobby). No automatic upgrade
is part of this project. The same static build can be served locally without an account.

Visitors can explore the six-stage/five-persona orchestration, inspect saved summaries,
step through synthetic records, examine review objections and original PDF sources, and
export Markdown. Fixture provenance stays visible. No provider request, mutation API,
database or owner laptop is needed. PDF.js loads on demand. This is an inspectable software
showcase, not a live research result. No fake agent timers or secret reasoning are shown.

After an explicit publication request, create a preview, verify provenance/stage selection,
walkthrough/PDF/export/mobile behavior and absence of privileged requests, then promote
the reviewed build. Linking automatic production deployments means later pushes to the
configured branch publish automatically; choose that behavior deliberately and retain
rollback versions. No deployment has been created in this task.

## Local live workspace

Run SQLite, files, API and worker on the same macOS/Linux laptop. Groq is the default
provider; account key + explicit verified free-plan acknowledgement are required for
real research. Gemini is secondary, explicitly selected. CPU parsing/embedding and the
bounded graph remain local; selected context is sent to the chosen provider. An offline
laptop cannot execute jobs. Quota pauses and unknown outcomes remain visible/recoverable.

Current official [Groq free limits](https://console.groq.com/docs/rate-limits) and
[structured-output support](https://console.groq.com/docs/structured-outputs) list
openai/gpt-oss-120b and 20b. Check the exact account before use; multi-stage context can
exhaust token-per-minute limits. Acknowledgement cannot prove billing status from a key.
No automatic upgrade, paid fallback, account rotation or quota evasion is implemented.

## Live public submissions are a separate design

The old optional Render API + Supabase Postgres + outbound laptop-worker plan is retired
for this SQLite revision. SQLite WAL assumes one host/local filesystem; a hosted API
cannot safely open the owner's laptop database over a network share. Ephemeral free
hosting filesystems also cannot hold durable job history/source files without a proven
persistent-storage plan. Hosting a React page alone does not solve these boundaries.

Before enabling public uploads/runs, design a remote coordination API or intentionally
restore a server database, scoped auth, bounded admissions, private object storage,
worker outbound transport, measured query-embedding service and recovery/backup behavior.
Start with owner-only submissions. No always-on multi-user live research service is
promised under ₹0. Keep the current public release read-only until these exist.

A reviewed real-run public replay is possible later, with consent/licensing review,
redaction and an explicit export loader. The current loader serves original synthetic
papers only. `scripts/export_run.py` exports report and source JSON, not PDF bytes; it
is not an automatic publication pipeline.
