import { useState } from "react";
import {
  ArrowRight,
  BookOpen,
  Check,
  ChevronLeft,
  ChevronRight,
  Compass,
  FileCheck2,
  FlaskConical,
  GitBranch,
  Layers3,
  Play,
  RotateCcw,
  Search,
  ShieldCheck,
  Timer,
  Workflow,
} from "lucide-react";
import type { Run } from "./types";

type Stage = {
  id: string;
  agent: string;
  task: string;
  detail: string;
  icon: typeof Compass;
};
const multi: Stage[] = [
  {
    id: "plan",
    agent: "Research lead",
    task: "Frame the question",
    detail:
      "Set the investigation direction within the frozen corpus and the run budget.",
    icon: Compass,
  },
  {
    id: "literature",
    agent: "Literature specialist",
    task: "Follow the evidence",
    detail:
      "Find relevant passages, identify coverage limits, and request bounded follow-up retrieval.",
    icon: BookOpen,
  },
  {
    id: "methods",
    agent: "Methods analyst",
    task: "Compare the methods",
    detail:
      "Extract datasets, baselines, metrics and conditions. Missing details remain unknown.",
    icon: Layers3,
  },
  {
    id: "candidates",
    agent: "Research lead",
    task: "Propose candidate gaps",
    detail:
      "Synthesize provisional candidates, then retrieve counterevidence before review.",
    icon: GitBranch,
  },
  {
    id: "review",
    agent: "Skeptical reviewer",
    task: "Challenge every candidate",
    detail:
      "Review claim support and challenge gaps using source passages. A candidate may be contradicted or unresolved.",
    icon: ShieldCheck,
  },
  {
    id: "experiments",
    agent: "Experiment designer",
    task: "Make it falsifiable",
    detail:
      "Propose tests only for candidates that provisionally survive review. Experiments are proposals; no experiment is executed.",
    icon: FlaskConical,
  },
];
const single: Stage[] = [
  {
    id: "single",
    agent: "Single researcher",
    task: "Investigate the corpus",
    detail:
      "One researcher extracts findings, a methods matrix and provisional candidates.",
    icon: Search,
  },
  {
    ...multi[4],
    agent: "Single researcher",
    detail:
      "The same researcher self-reviews its candidates. This mode has no independent reviewer persona.",
  },
  {
    ...multi[5],
    agent: "Single researcher",
    detail: "The same researcher proposes tests after self-review.",
  },
];

export function Orchestration({
  run,
  openEvidence,
  onReview,
}: {
  run: Run;
  openEvidence: (id: string) => void;
  onReview: () => void;
}) {
  const [selected, setSelected] = useState("");
  const [cursor, setCursor] = useState<number | null>(null);
  const fixture = run.provider === "fixture";
  const stages =
    run.mode === "multi"
      ? multi
      : run.mode === "single"
        ? single
        : [
            {
              id: "rag",
              agent: "RAG generator",
              task: "Answer from retrieval",
              detail:
                "One generation uses retrieved passages. No specialist handoffs or independent review occur in this mode.",
              icon: FileCheck2,
            },
          ];
  const records = (run.events || []).filter((e) =>
    stages.some((s) => s.id === e.node),
  );
  const walking = cursor !== null;
  const visible = walking ? records.slice(0, cursor + 1) : records;
  const stageEvents = (id: string) => visible.filter((e) => e.node === id);
  const status = (id: string) => {
    const last = stageEvents(id).at(-1);
    if (!last) return "Awaiting record";
    if (["completed", "cache_hit"].includes(last.kind)) return "Recorded";
    if (last.kind === "started") {
      if (walking) return "Started in record";
      if (["waiting_for_quota", "paused"].includes(run.status)) return "Paused";
      if (["cancelled", "failed"].includes(run.status)) return "Stopped";
      return run.status === "running" ? "Running" : "Outcome unrecorded";
    }
    return last.kind.replaceAll("_", " ");
  };
  const active =
    stages.find((s) => s.id === selected) ||
    stages.find((s) => s.id === visible.at(-1)?.node) ||
    stages[0];
  const logs = stageEvents(active.id);
  const done = stages.filter((s) => status(s.id) === "Recorded").length;
  const refs = [...new Set(logs.flatMap((e) => e.data.evidence_ids || []))];
  const inspected = new Set((run.result?.evidence || []).map((p) => p.id));
  const related = [
    ...new Set(
      (!walking && status(active.id) === "Recorded"
        ? (active.id === "methods"
            ? run.result?.matrix.flatMap((r) => r.citations)
            : active.id === "review"
              ? run.result?.reviews.flatMap((r) => r.counterevidence)
              : active.id === "candidates"
                ? run.result?.gaps.flatMap((r) => r.citations)
                : active.id === "literature" ||
                    active.id === "single" ||
                    active.id === "rag"
                  ? run.result?.claims.flatMap((r) => r.citations)
                  : []) || []
        : []
      ).map((c) => c.evidence_id),
    ),
  ].filter((id) => inspected.has(id));
  const reviewed = status("review") === "Recorded";

  return (
    <section className="orchestration" aria-label="Agent orchestration">
      <div className="orchestration-heading">
        <div>
          <div className="eyebrow">
            <Workflow size={14} /> THE INVESTIGATION, UNFOLDED
          </div>
          <h2>
            {run.mode === "multi"
              ? "Five specialists. One evidence trail."
              : run.mode === "single"
                ? "One researcher. Three bounded stages."
                : "Retrieval, followed by one answer."}
          </h2>
          <p className="muted">
            {run.mode === "multi"
              ? "Sequential handoffs · the research lead returns for synthesis · review precedes proposals."
              : "The map reflects the selected run mode and its recorded events."}
          </p>
        </div>
        <div className="orchestration-progress">
          <strong>
            {done}
            <span> / {stages.length}</span>
          </strong>
          <small>stages with saved outputs</small>
        </div>
      </div>

      <div className="orchestration-toolbar">
        <span className="trace-label">
          <span
            className={
              "status-dot " +
              (!fixture && run.status === "running" && !walking ? "green" : "")
            }
          />
          {walking
            ? "Fixture walkthrough"
            : fixture
              ? "Synthetic fixture records"
              : "Persisted worker events"}
        </span>
        {fixture && records.length > 0 && !walking && (
          <button
            className="button"
            onClick={() => {
              setCursor(0);
              setSelected(records[0].node);
            }}
          >
            <Play size={13} /> Walk through fixture
          </button>
        )}
        {walking && (
          <div className="walk-controls">
            <button
              className="icon-button"
              aria-label="Previous recorded event"
              disabled={cursor === 0}
              onClick={() => {
                const n = Math.max(0, cursor - 1);
                setCursor(n);
                setSelected(records[n].node);
              }}
            >
              <ChevronLeft size={17} />
            </button>
            <span aria-live="polite">
              Record {cursor + 1} of {records.length}
            </span>
            <button
              className="icon-button"
              aria-label="Next recorded event"
              disabled={cursor >= records.length - 1}
              onClick={() => {
                const n = Math.min(records.length - 1, cursor + 1);
                setCursor(n);
                setSelected(records[n].node);
              }}
            >
              <ChevronRight size={17} />
            </button>
            <button
              className="button subtle"
              onClick={() => {
                setCursor(null);
                setSelected("");
              }}
            >
              <RotateCcw size={13} /> Show all records
            </button>
          </div>
        )}
      </div>
      {walking && (
        <p className="walk-disclosure" role="status">
          Stepping through synthetic saved records. No agents are running and no
          model calls are being made.
        </p>
      )}

      <div className="agent-workspace">
        <ol className="agent-map" aria-label="Recorded research stages">
          {stages.map((stage, i) => {
            const state = status(stage.id);
            const Icon = stage.icon;
            return (
              <li key={stage.id}>
                <button
                  className={
                    "agent-node " +
                    (active.id === stage.id ? "is-selected " : "") +
                    (state === "Recorded"
                      ? "is-recorded"
                      : state === "Running"
                        ? "is-running"
                        : "")
                  }
                  aria-pressed={active.id === stage.id}
                  aria-label={`${i + 1}. ${stage.agent}: ${stage.task}`}
                  onClick={() => setSelected(stage.id)}
                >
                  <div className="agent-node-top">
                    <span className="agent-symbol">
                      <Icon size={20} />
                    </span>
                    <span className="agent-step">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                  </div>
                  <span className="agent-persona">{stage.agent}</span>
                  <strong>{stage.task}</strong>
                  <span className="agent-state">
                    {state === "Recorded" ? (
                      <Check size={12} />
                    ) : (
                      <Timer size={12} />
                    )}
                    {state}
                  </span>
                </button>
                {i < stages.length - 1 && (
                  <span className="handoff-arrow" aria-hidden="true">
                    <ArrowRight size={16} />
                  </span>
                )}
              </li>
            );
          })}
        </ol>

        <aside className="agent-inspector" aria-label="Selected stage details">
          <div className="eyebrow">
            STAGE DETAILS <span>{status(active.id)}</span>
          </div>
          <h3>{active.agent}</h3>
          <p>{active.detail}</p>
          <div className="inspector-divider" />
          <h4>Saved output</h4>
          {logs.length ? (
            logs.map((event, i) => (
              <div className="stage-log" key={event.id || i}>
                <span className="stage-log-kind">
                  {event.kind.replaceAll("_", " ")}
                  {event.duration_ms != null
                    ? ` · ${event.duration_ms} ms`
                    : " · duration not recorded"}
                </span>
                <p>
                  {event.data.summary ||
                    event.data.message ||
                    (event.kind === "started"
                      ? "The worker persisted a call intent before contacting the provider."
                      : event.kind === "cache_hit"
                        ? "A previously saved extraction was reused."
                        : "Event saved without a summary.")}
                </p>
              </div>
            ))
          ) : (
            <p className="muted">
              No event recorded for this stage
              {walking ? " at this walkthrough step" : ""}. Its position in the
              map does not establish execution.
            </p>
          )}
          {refs.length > 0 && (
            <div className="stage-evidence">
              <h4>Evidence in this event</h4>
              {refs
                .filter((id) => inspected.has(id))
                .map((id, i) => (
                  <button
                    className="citation"
                    key={id}
                    onClick={() => openEvidence(id)}
                  >
                    Source {i + 1}
                    <ArrowRight size={12} />
                  </button>
                ))}
              {refs.some((id) => !inspected.has(id)) && (
                <p className="muted small">
                  Some event references are not in the currently available
                  evidence artifact.
                </p>
              )}
            </div>
          )}
          {related.length > 0 && (
            <div className="stage-evidence">
              <h4>Related evidence in final artifact</h4>
              {related.map((id, i) => (
                <button
                  className="citation"
                  key={id}
                  onClick={() => openEvidence(id)}
                >
                  Artifact source {i + 1}
                  <ArrowRight size={12} />
                </button>
              ))}
            </div>
          )}
        </aside>
      </div>

      <div className="orchestration-outcomes">
        <div>
          <span className="outcome-icon">
            <BookOpen size={18} />
          </span>
          <div>
            <strong>{run.manifest.length} papers, frozen in scope</strong>
            <p>Versioned sources keep citations tied to the same corpus.</p>
          </div>
        </div>
        <div>
          <span className="outcome-icon">
            <ShieldCheck size={18} />
          </span>
          <div>
            <strong>
              {reviewed
                ? `${run.result?.reviews.filter((r) => r.disposition === "contradicted").length || 0} candidates contradicted`
                : "Review has no saved output yet"}
            </strong>
            <p>
              {reviewed
                ? "Inspect objections and counterevidence before accepting a gap."
                : "Review decisions appear after the relevant stage is recorded."}
            </p>
            {reviewed && (
              <button className="text-button" onClick={onReview}>
                Open gap review <ArrowRight size={13} />
              </button>
            )}
          </div>
        </div>
        <div>
          <span className="outcome-icon">
            <FlaskConical size={18} />
          </span>
          <div>
            <strong>
              {status("experiments") === "Recorded"
                ? `${run.result?.experiments.length || 0} experiment proposals`
                : run.mode === "rag"
                  ? "No experiment stage in RAG"
                  : "Proposals await a saved output"}
            </strong>
            <p>
              Falsifiable next steps remain provisional and require human
              review.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
