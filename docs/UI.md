# Interface and orchestration

The interface uses a light graphite neumorphic material: raised containers, inset
controls, slate copy and teal emphasis. Cards keep visible borders and text states;
shadow, color and motion are never the sole status indicators. Keyboard focus is
outlined, the PDF drawer traps/restores focus, reduced-motion disables transitions,
and forced-colors adds explicit boundaries to controls and selected stages.

## Opening experience

Orchestration opens by default for an investigation. Summary metrics remain available
on the other investigation panels; the opening view prioritizes the agent map. The
question, scope, provenance, frozen paper count, run status and export remain visible.
On narrow screens the numbered stages wrap into two columns; arrows follow a
serpentine sequence. The graph is sequential, matching the backend's bounded workflow.
It does not imply parallel agents or autonomous deployment agents.

`frontend/src/Orchestration.tsx` derives stage states from persisted event node/kind
values, alongside run status. A `completed` event or extraction `cache_hit` establishes
a recorded output. A `started` event alone does not establish completion. Paused and
stopped runs retain that distinction; absent events say **Awaiting record**. The
progress count describes saved model-stage outputs, not overall run completion:
retrieval tools and final report persistence are separate backend steps. The full
tool/event history, budgets and frozen manifest are in Activity & scope.

Multi mode has five personas across six model stages: Research lead (plan), Literature
specialist, Methods analyst, Research lead (candidates), Skeptical reviewer and
Experiment designer. Single mode shows the same researcher across investigation,
self-review and proposals. RAG shows a single generator. These are bounded roles,
not claims of independent human researchers or unrestricted autonomy.

## Evidence and walkthrough provenance

Stage details show saved event summaries and measured durations only when present.
Event evidence IDs and related final-artifact citations have separate labels. Only
IDs available in the run evidence artifact offer source buttons. Final artifacts are
not presented as contemporaneous tool decisions. The UI displays observable summaries
and results; it does not invent private model reasoning or fabricate activity.

Fixture runs additionally expose **Walk through fixture**. This is an explicit manual
cursor over synthetic event records, with no timers, provider requests or new worker
jobs. It never updates the actual run status. Later stage statuses and final-artifact
source links are withheld until the walkthrough exits; review/proposal totals appear
only after their relevant saved stage has been reached. No scientific claim follows
from a deterministic fixture. A real-run replay is not shipped in this revision.

PDF.js and its rendering code are loaded lazily when evidence opens. The viewer still
renders the actual source PDF page and preserves honest page/text fallback behavior.

## Verification

Four Chromium flows cover existing evidence/export/reload and mobile retrieval,
stage selection/artifact evidence, fixture stepping without future review decisions,
and a synthetic single-researcher quota-paused state. The latter intercepts a fixture
response deliberately; it does not verify a live worker or provider. Screenshots of
desktop and mobile were inspected. See VERIFICATION.md for pending backend checks and
DEPLOYMENT.md for the static showcase versus live workspace release sequence.

The SQLite/Groq revision makes Groq the setup default. Submission is disabled until
health confirms server configuration; fixture remains an explicit selection. Completed
local fixture runs display a synthetic banner even outside static example mode. The
isolated local browser suite exercises the actual SQLite/API/worker path with fixtures.
