import React, { lazy, Suspense, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowDownToLine,
  ArrowRight,
  BookOpen,
  Check,
  ChevronRight,
  Clock3,
  Database,
  FileText,
  FlaskConical,
  FolderOpen,
  History,
  Layers3,
  Link2,
  LoaderCircle,
  Microscope,
  Plus,
  Search,
  ShieldCheck,
  Square,
  Terminal,
  Upload,
  X,
  PanelRightOpen,
} from "lucide-react";
import { api, request, download, setOwnerToken } from "./api";
import { Orchestration } from "./Orchestration";
import type { Run, Passage, Collection, Paper, Citation } from "./types";
import "./style.css";
import "./neumorphic.css";

const PdfPreview = lazy(() =>
  import("./PdfPreview").then((module) => ({ default: module.PdfPreview })),
);

type Screen = "workspace" | "library" | "setup" | "history" | "retrieval";
const modes: Record<string, string> = {
  rag: "Ordinary RAG",
  single: "Single research agent",
  multi: "Five-role investigation",
};
const date = (value: string | null) =>
  value ? new Date(value).toLocaleString() : "Static fixture";
function Badge({
  children,
  tone = "",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
function App() {
  const demoOnly = import.meta.env.MODE === "demo";
  const [example, setExample] = useState(import.meta.env.MODE === "demo");
  const [screen, setScreen] = useState<Screen>("workspace");
  const [tab, setTab] = useState("Orchestration");
  const [run, setRun] = useState<Run | null>(null);
  const [history, setHistory] = useState<Run[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [collection, setCollection] = useState("");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [health, setHealth] = useState<{
    database: string;
    worker: { online: boolean };
    read_only: boolean;
    gemini_configured?: boolean;
  } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [evidence, setEvidence] = useState<Passage | null>(null);
  const [neighbors, setNeighbors] = useState<Passage[]>([]);
  const [query, setQuery] = useState("memory retrieval ordering");
  const [hits, setHits] = useState<Passage[]>([]);
  const [question, setQuestion] = useState(
    "How should memory retrieval ordering be evaluated under distractors?",
  );
  const [scope, setScope] = useState(
    "Agent memory and long-context reliability; uploaded corpus only.",
  );
  const [provider, setProvider] = useState("fixture");
  const [mode, setMode] = useState("multi");
  const [budget, setBudget] = useState({
    max_calls: 10,
    max_tokens: 60000,
    max_output_tokens: 1800,
    max_tool_calls: 12,
    max_followups: 2,
    review_rounds: 1,
    retrieval_k: 8,
    paper_diversity: 3,
  });
  const [collectionName, setCollectionName] = useState("");
  const [token, setToken] = useState("");
  const [revision, setRevision] = useState(0);
  const [duplicateAck, setDuplicateAck] = useState(false);
  const [resumeLimits, setResumeLimits] = useState<{
    max_calls?: number;
    max_tokens?: number;
  }>({});
  const previousFocus = useRef<HTMLElement | null>(null);
  const dialog = useRef<HTMLDivElement>(null);
  const readOnly = example || health?.read_only;

  async function action(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await work();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    let active = true;
    setRun(null);
    setError("");
    setHits([]);
    setEvidence(null);
    setCollections([]);
    setPapers([]);
    if (example) {
      void fetch("/examples/run.json")
        .then((r) => {
          if (!r.ok) throw new Error("Example unavailable");
          return r.json();
        })
        .then((r: Run) => {
          if (active) {
            setRun(r);
            setHistory([r]);
            setCollections([
              {
                id: r.collection_id,
                name: "Memory & context · synthetic",
                scope: r.scope,
              },
            ]);
            setCollection(r.collection_id);
          }
        })
        .catch((e) => {
          if (active) setError(String(e));
        });
    } else {
      const refresh = async () => {
        try {
          const h = await api("/health");
          if (active) setHealth(h);
          if (h.database === "online") {
            const [cs, rs] = await Promise.all([
              api("/collections"),
              api("/runs"),
            ]);
            if (active) {
              setCollections(cs);
              setHistory(rs);
              setCollection((c) =>
                cs.some((x: Collection) => x.id === c) ? c : cs[0]?.id || "",
              );
            }
          }
        } catch {
          if (active) setHealth(null);
        }
      };
      void refresh();
      const timer = setInterval(() => void refresh(), 5000);
      return () => {
        active = false;
        clearInterval(timer);
      };
    }
    return () => {
      active = false;
    };
  }, [example, revision]);
  useEffect(() => {
    if (example || !collection) return;
    let active = true;
    const refresh = () =>
      api(`/collections/${collection}/papers`)
        .then((p) => {
          if (active) setPapers(p);
        })
        .catch(() => {});
    void refresh();
    const timer = setInterval(() => void refresh(), 3000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [collection, example]);
  useEffect(() => {
    if (example || !run) return;
    let active = true;
    const refresh = () =>
      api(`/runs/${run.id}`)
        .then((r) => {
          if (active) setRun(r);
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    void refresh();
    const timer = setInterval(() => void refresh(), 3000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [run?.id, example]);
  useEffect(() => {
    if (!evidence) return;
    previousFocus.current = document.activeElement as HTMLElement;
    dialog.current?.focus();
    const listener = (event: KeyboardEvent) => {
      if (event.key === "Escape") setEvidence(null);
      if (event.key === "Tab" && dialog.current) {
        const elements = dialog.current.querySelectorAll<HTMLElement>(
          'button,a,input,[tabindex="0"]',
        );
        const first = elements[0],
          last = elements[elements.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", listener);
    return () => {
      document.removeEventListener("keydown", listener);
      previousFocus.current?.focus();
    };
  }, [evidence]);

  async function openEvidence(id: string) {
    setNeighbors([]);
    const saved =
      run?.result?.evidence.find((e) => e.id === id) ||
      hits.find((e) => e.id === id);
    if (example) {
      if (saved) setEvidence(saved);
      else setError("Evidence missing from this exported example");
      return;
    }
    await action(async () => {
      const result = await api(
        `/collections/${hits.some((p) => p.id === id) ? collection : run?.collection_id || collection}/evidence/${id}`,
      );
      setEvidence({ ...result.passage, title: result.passage.title });
      setNeighbors(result.neighbors);
    });
  }
  function citations(refs: Citation[] = []) {
    return (
      <div className="citations">
        {refs.map((c, i) => (
          <button
            className="citation"
            key={c.evidence_id + i}
            onClick={() => void openEvidence(c.evidence_id)}
            title={c.quote}
          >
            <Link2 size={12} /> Source {i + 1}
            <ChevronRight size={12} />
          </button>
        ))}
      </div>
    );
  }
  async function exportReport() {
    if (!run) return;
    await action(async () => {
      const text = example
        ? run.report!
        : await (await request(`/runs/${run.id}/report`)).text();
      download(text, `research-${run.id}.md`);
    });
  }
  async function runControl(control: string) {
    if (!run) return;
    await action(async () => {
      await api(`/runs/${run.id}/${control}`, {
        method: "POST",
        ...(control === "resume"
          ? {
              body: JSON.stringify({
                acknowledge_duplicate_call: duplicateAck,
                ...(Object.keys(resumeLimits).length
                  ? { budget: { ...run.config?.budget, ...resumeLimits } }
                  : {}),
              }),
            }
          : {}),
      });
      setRun(await api(`/runs/${run.id}`));
    });
  }
  const result = run?.result;
  const survived =
    result?.reviews.filter((r) => r.disposition === "survived").length || 0;
  const challenged =
    result?.reviews.filter((r) => r.disposition === "contradicted").length || 0;
  const iconSize = 17;
  const nav = [
    ["workspace", "Investigation", Microscope],
    ["library", "Collection library", FolderOpen],
    ["retrieval", "Retrieval inspector", Search],
    ["history", "Run history", History],
  ] as const;
  return (
    <div
      className={
        "app" +
        (screen === "workspace" && tab === "Orchestration" && run
          ? " orchestration-view"
          : "")
      }
    >
      <a className="skip" href="#main">
        Skip to workspace
      </a>
      <aside className="sidebar">
        <a
          href="#"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            setScreen("workspace");
          }}
        >
          <span className="brand-icon">
            <Layers3 size={22} />
          </span>
          <span>
            Research Gap<span className="brand-small">INVESTIGATOR</span>
          </span>
        </a>
        <div className="workspace-label">
          PERSONAL WORKSPACE <span>V1</span>
        </div>
        <nav aria-label="Main navigation">
          {nav.map(([key, label, Icon]) => (
            <button
              key={key}
              className={screen === key ? "nav-item active" : "nav-item"}
              onClick={() => setScreen(key)}
            >
              <Icon size={iconSize} />
              {label}
              {screen === key && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-section">
          <div className="workspace-label">
            COLLECTIONS{" "}
            <button
              aria-label="New collection"
              disabled={!!readOnly}
              onClick={() => setScreen("library")}
            >
              <Plus size={14} />
            </button>
          </div>
          {collections.length ? (
            collections.map((c) => (
              <button
                className="collection-nav"
                key={c.id}
                onClick={() => {
                  setCollection(c.id);
                  setScreen("library");
                }}
              >
                <span className="collection-square" />
                {c.name}
              </button>
            ))
          ) : (
            <p className="muted small">Your papers start here.</p>
          )}
        </div>
        <div className="sidebar-bottom">
          <div className="local-card">
            <span
              className={
                "status-dot " +
                (!example && health?.worker.online ? "green" : "")
              }
            />
            <strong>
              {example
                ? "Example explorer"
                : health?.worker.online
                  ? "Local worker online"
                  : "Local worker offline"}
            </strong>
            <p>
              {example
                ? "Read-only · no API required"
                : "Jobs persist while your browser is closed."}
            </p>
          </div>
          <div className="profile">
            <span className="avatar">J</span>
            <div>
              Jeeth’s research lab<small>Local compute · ₹0 required</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <span>
              {screen === "setup"
                ? "New investigation"
                : screen === "library"
                  ? "Collection library"
                  : screen === "history"
                    ? "Run history"
                    : screen === "retrieval"
                      ? "Retrieval inspector"
                      : "Investigation"}
            </span>
          </div>
          <div className="top-actions">
            <span className="small muted">
              {example ? "STATIC EXAMPLE" : "LOCAL WORKSPACE"}
            </span>
            <button
              className="button subtle"
              disabled={demoOnly}
              title={
                demoOnly
                  ? "Static read-only build. Start npm run dev to use the local API."
                  : undefined
              }
              onClick={() => {
                if (!demoOnly) setExample(!example);
                setScreen("workspace");
              }}
            >
              {demoOnly
                ? "Read-only explorer"
                : example
                  ? "Open local workspace"
                  : "Explore example"}
              <ArrowRight size={14} />
            </button>
          </div>
        </header>
        <main id="main">
          <div className="eyebrow">
            <span className="red-line" /> EVIDENCE-FIRST RESEARCH
          </div>
          <div className="page-heading">
            <div>
              <h1>
                {screen === "library"
                  ? "Your literature, traceable."
                  : screen === "setup"
                    ? "Start with a focused question."
                    : screen === "retrieval"
                      ? "Inspect what retrieval found."
                      : screen === "history"
                        ? "A record of every investigation."
                        : "From papers to better questions."}
              </h1>
              <p className="intro">
                {screen === "library"
                  ? "Preserve original sources, document versions, and every ingestion outcome."
                  : screen === "retrieval"
                    ? "Compare keyword and vector ranks. Follow every passage back to its source."
                    : screen === "setup"
                      ? "Set the scope and limits before the worker begins."
                      : screen === "history"
                        ? "Reopen persisted runs and their frozen corpus."
                        : "Compare the evidence. Challenge candidate gaps. Design falsifiable experiments."}
              </p>
            </div>
            {screen !== "setup" && (
              <button
                className="button primary"
                disabled={!!readOnly || busy}
                onClick={() => setScreen("setup")}
              >
                <Plus size={16} />
                New investigation
              </button>
            )}
          </div>
          {error && (
            <div className="notice error" role="alert">
              <span>{error}</span>
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {example && (
            <div className="notice fixture">
              <FlaskConical size={18} />
              <div>
                <strong>Synthetic example · read-only</strong>
                <span>
                  Original toy papers and deterministic fixture responses. This
                  is a software demonstration, not a real research run.
                </span>
              </div>
              <Badge>NO LLM CALLS</Badge>
            </div>
          )}
          {!example && (!health || health.database !== "online") && (
            <div className="notice">
              <Database size={18} />
              <div>
                <strong>Local services unavailable</strong>
                <span>
                  Start PostgreSQL, apply migrations, and run the API. The
                  example explorer works without services or keys.
                </span>
              </div>
              <button className="button" onClick={() => setExample(true)}>
                Explore example <ArrowRight size={14} />
              </button>
            </div>
          )}
          {!example && health?.read_only && (
            <div className="notice">
              <ShieldCheck size={18} />
              This backend is read-only. Uploads and run creation are disabled.
            </div>
          )}
          {busy && (
            <div className="request-status" role="status">
              <LoaderCircle className="spin" size={14} /> Saving or loading…
            </div>
          )}

          {screen === "workspace" && (
            <>
              {run ? (
                <>
                  <section className="run-summary">
                    <div className="run-heading">
                      <div>
                        <div className="small muted mono">
                          {example ? "EXAMPLE INVESTIGATION" : "INVESTIGATION"}{" "}
                          <span className="separator">/</span>{" "}
                          {run.id.slice(0, 8)}
                        </div>
                        <h2>{run.question}</h2>
                      </div>
                      <Badge tone={run.status === "complete" ? "success" : ""}>
                        <span className="status-dot" />
                        {run.status.replaceAll("_", " ")}
                      </Badge>
                    </div>
                    <p className="muted scope">{run.scope}</p>
                    <div className="run-meta">
                      <span>
                        <BookOpen size={14} />
                        {run.manifest?.length || 0} frozen papers
                      </span>
                      <span>
                        <Layers3 size={14} />
                        {modes[run.mode]}
                      </span>
                      <span>
                        <Clock3 size={14} />
                        {date(run.created_at)}
                      </span>
                      <button
                        className="button subtle export"
                        disabled={!run.report || busy}
                        onClick={() => void exportReport()}
                      >
                        <ArrowDownToLine size={15} />
                        Export report
                      </button>
                    </div>
                    {!example && (
                      <div className="run-controls">
                        <span className="small muted">
                          {health?.worker.online
                            ? "Worker online"
                            : "Worker offline · queued work waits for your laptop"}
                        </span>
                        {[
                          "queued",
                          "running",
                          "waiting_for_quota",
                          "paused",
                        ].includes(run.status) && (
                          <button
                            className="button"
                            onClick={() => void runControl("cancel")}
                          >
                            <Square size={12} />
                            Cancel
                          </button>
                        )}
                        {["paused", "waiting_for_quota"].includes(
                          run.status,
                        ) && (
                          <button
                            className="button"
                            onClick={() => void runControl("resume")}
                          >
                            Resume
                          </button>
                        )}
                        {["paused", "waiting_for_quota"].includes(
                          run.status,
                        ) && (
                          <div className="resume-options">
                            <label>
                              Call limit
                              <input
                                type="number"
                                min={1}
                                max={20}
                                value={
                                  resumeLimits.max_calls ??
                                  run.config?.budget.max_calls ??
                                  10
                                }
                                onChange={(e) =>
                                  setResumeLimits((v) => ({
                                    ...v,
                                    max_calls: Number(e.target.value),
                                  }))
                                }
                              />
                            </label>
                            <label>
                              Token budget
                              <input
                                type="number"
                                min={1000}
                                max={100000}
                                value={
                                  resumeLimits.max_tokens ??
                                  run.config?.budget.max_tokens ??
                                  60000
                                }
                                onChange={(e) =>
                                  setResumeLimits((v) => ({
                                    ...v,
                                    max_tokens: Number(e.target.value),
                                  }))
                                }
                              />
                            </label>
                            <label className="acknowledgement">
                              <input
                                type="checkbox"
                                checked={duplicateAck}
                                onChange={(e) =>
                                  setDuplicateAck(e.target.checked)
                                }
                              />
                              I acknowledge that retrying an uncertain call may
                              consume quota twice.
                            </label>
                          </div>
                        )}
                        {run.error && <p role="status">{run.error}</p>}
                      </div>
                    )}
                  </section>
                  <div className="stats-grid">
                    <div>
                      <span>PAPERS IN SCOPE</span>
                      <strong>
                        {run.manifest?.length || 0}
                        <BookOpen size={21} />
                      </strong>
                      <small>Frozen document versions</small>
                    </div>
                    <div>
                      <span>INSPECTABLE PASSAGES</span>
                      <strong>
                        {result?.evidence.length ?? "—"}
                        <Link2 size={21} />
                      </strong>
                      <small>Exact source references</small>
                    </div>
                    <div>
                      <span>CANDIDATES AFTER REVIEW</span>
                      <strong>
                        {survived}
                        <Microscope size={21} />
                      </strong>
                      <small>Provisional · never a novelty verdict</small>
                    </div>
                    <div>
                      <span>CHALLENGED CANDIDATES</span>
                      <strong>
                        {challenged}
                        <ShieldCheck size={21} />
                      </strong>
                      <small>Counterevidence recorded</small>
                    </div>
                  </div>
                  <div
                    className="tabbar"
                    role="tablist"
                    aria-label="Investigation panels"
                  >
                    {[
                      "Orchestration",
                      "Findings",
                      "Literature matrix",
                      "Gap review",
                      "Activity & scope",
                    ].map((t) => (
                      <button
                        role="tab"
                        aria-selected={tab === t}
                        className={tab === t ? "selected" : ""}
                        key={t}
                        onClick={() => setTab(t)}
                      >
                        {t}
                        {t === "Gap review" && (
                          <span>{result?.gaps.length || 0}</span>
                        )}
                      </button>
                    ))}
                  </div>
                  {tab === "Orchestration" && (
                    <Orchestration
                      key={run.id}
                      run={run}
                      openEvidence={(id) => void openEvidence(id)}
                      onReview={() => setTab("Gap review")}
                    />
                  )}
                  {tab === "Findings" && (
                    <div className="findings-layout">
                      <section>
                        <div className="section-heading">
                          <h3>What the evidence supports</h3>
                          <span className="muted small">
                            Separate support review
                          </span>
                        </div>
                        {result?.claims.length ? (
                          result.claims.map((claim, i) => {
                            const judgment = result.support_reviews.find(
                              (j) => j.claim_index === i,
                            );
                            return (
                              <article className="finding-card" key={i}>
                                <div className="card-top">
                                  <Badge>
                                    {claim.category.replaceAll("_", " ")}
                                  </Badge>
                                  <Badge
                                    tone={
                                      judgment?.judgment === "supported"
                                        ? "success"
                                        : "warning"
                                    }
                                  >
                                    {judgment?.judgment || "Unreviewed"}
                                  </Badge>
                                </div>
                                <h4>{claim.text}</h4>
                                <p className="muted">
                                  {judgment?.reason ||
                                    "No separate semantic support judgment is available."}
                                </p>
                                {citations(claim.citations)}
                              </article>
                            );
                          })
                        ) : (
                          <div className="empty">
                            <Terminal size={25} />
                            <h3>
                              {run.status === "complete"
                                ? "No supported findings recorded"
                                : "Waiting for persisted findings"}
                            </h3>
                            <p>
                              The worker records results as each real stage
                              completes.
                            </p>
                          </div>
                        )}
                        <div className="section-heading lower">
                          <h3>Candidate questions</h3>
                          <button
                            className="text-button"
                            onClick={() => setTab("Gap review")}
                          >
                            View review <ArrowRight size={14} />
                          </button>
                        </div>
                        {result?.gaps.map((gap, i) => (
                          <button
                            className="gap-preview"
                            key={gap.id}
                            onClick={() => setTab("Gap review")}
                          >
                            <span className="index-number">0{i + 1}</span>
                            <div>
                              <strong>{gap.description}</strong>
                              <small>
                                {gap.kind.replaceAll("_", " ")} ·{" "}
                                {result.reviews.find((r) => r.gap_id === gap.id)
                                  ?.disposition || "unreviewed"}
                              </small>
                            </div>
                            <ChevronRight size={18} />
                          </button>
                        ))}
                      </section>
                      <aside className="context-card">
                        <div className="card-icon">
                          <ShieldCheck size={20} />
                        </div>
                        <h3>A gap is a question to test.</h3>
                        <p>
                          Review can reject a candidate, reveal missing context,
                          or leave a scoped hypothesis worth investigating.
                        </p>
                        <div className="rule" />
                        <h4>Research boundaries</h4>
                        <ul>
                          <li>Uploaded corpus only</li>
                          <li>No external prior-work search</li>
                          <li>No automatic experiments</li>
                          <li>Human review still required</li>
                        </ul>
                        <button
                          className="text-button"
                          onClick={() => setTab("Activity & scope")}
                        >
                          Inspect scope & provenance <ArrowRight size={14} />
                        </button>
                      </aside>
                    </div>
                  )}
                  {tab === "Literature matrix" && (
                    <section>
                      <div className="section-heading">
                        <h3>Compare the conditions first</h3>
                        <Badge>Unknown stays unknown</Badge>
                      </div>
                      <p className="muted">
                        Values require evidence. Different settings do not
                        establish a like-for-like comparison.
                      </p>
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              {[
                                "Paper",
                                "Methods",
                                "Datasets",
                                "Baselines",
                                "Metrics",
                                "Conditions",
                                "Results",
                                "Limitations",
                                "Evidence",
                              ].map((c) => (
                                <th key={c}>{c}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {result?.matrix.map((row, i) => (
                              <tr key={row.paper_id + i}>
                                <td>
                                  {run.manifest.find(
                                    (p) => p.paper_id === row.paper_id,
                                  )?.title || row.paper_id}
                                </td>
                                {(
                                  [
                                    "methods",
                                    "datasets",
                                    "baselines",
                                    "metrics",
                                    "conditions",
                                    "results",
                                    "limitations",
                                  ] as const
                                ).map((k) => (
                                  <td
                                    key={k}
                                    className={
                                      row[k] === "unknown" ? "unknown" : ""
                                    }
                                  >
                                    {row[k]}
                                  </td>
                                ))}
                                <td>{citations(row.citations)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      {!result?.matrix.length && (
                        <div className="empty">
                          No extraction rows recorded yet.
                        </div>
                      )}
                    </section>
                  )}
                  {tab === "Gap review" && (
                    <section>
                      <div className="section-heading">
                        <h3>Try to disprove the candidate.</h3>
                        <span className="muted small">
                          Review before experiment design
                        </span>
                      </div>
                      {result?.gaps.map((gap, i) => {
                        const review = result.reviews.find(
                          (r) => r.gap_id === gap.id,
                        );
                        const exp = result.experiments.find(
                          (e) => e.gap_id === gap.id,
                        );
                        return (
                          <article className="review-card" key={gap.id}>
                            <div className="card-top">
                              <span className="mono muted small">
                                CANDIDATE 0{i + 1}
                              </span>
                              <Badge
                                tone={
                                  review?.disposition === "survived"
                                    ? "success"
                                    : review?.disposition === "contradicted"
                                      ? "danger"
                                      : "warning"
                                }
                              >
                                {review?.disposition || "unreviewed"}
                              </Badge>
                            </div>
                            <h3>{gap.description}</h3>
                            <p>{gap.significance}</p>
                            <Badge>{gap.kind.replaceAll("_", " ")}</Badge>
                            <div className="review-columns">
                              <div>
                                <h4>Supporting evidence</h4>
                                {citations(gap.citations)}
                                {gap.citations.map((c, j) => (
                                  <blockquote key={j}>{c.quote}</blockquote>
                                ))}
                                <h4>Open concerns</h4>
                                <p className="muted">{gap.concerns}</p>
                              </div>
                              <div>
                                <h4>
                                  <ShieldCheck size={15} /> Skeptical review
                                </h4>
                                <p>
                                  {review?.rationale || "No review recorded."}
                                </p>
                                {citations(review?.counterevidence)}
                                {review?.counterevidence.map((c, j) => (
                                  <blockquote key={j}>{c.quote}</blockquote>
                                ))}
                                <p className="muted">{review?.unresolved}</p>
                              </div>
                            </div>
                            {exp && (
                              <details className="experiment">
                                <summary>
                                  <FlaskConical size={16} />
                                  Proposed experiment · not executed
                                  <ChevronRight size={16} />
                                </summary>
                                <dl>
                                  {Object.entries(exp)
                                    .filter(([k]) => k !== "gap_id")
                                    .map(([k, v]) => (
                                      <React.Fragment key={k}>
                                        <dt>{k}</dt>
                                        <dd>{v}</dd>
                                      </React.Fragment>
                                    ))}
                                </dl>
                              </details>
                            )}
                          </article>
                        );
                      })}
                      {!result?.gaps.length && (
                        <div className="empty">
                          No candidate gaps recorded. Abstention is a valid
                          outcome.
                        </div>
                      )}
                    </section>
                  )}
                  {tab === "Activity & scope" && (
                    <section>
                      <div className="section-heading">
                        <h3>Persisted activity</h3>
                        <Badge>
                          {example ? "Fixture records" : "Actual worker events"}
                        </Badge>
                      </div>
                      <div className="usage">
                        <span>
                          Model calls <strong>{run.calls}</strong>
                        </span>
                        <span>
                          Tokens{" "}
                          <strong>
                            {run.usage_unknown
                              ? "unknown (conservative budget accounting)"
                              : run.tokens}
                          </strong>
                        </span>
                        <span>
                          Provider <strong>{run.provider}</strong>
                        </span>
                        <span>
                          Tools <strong>{run.tool_calls ?? "—"}</strong>
                        </span>
                      </div>
                      <div className="timeline">
                        {run.events?.map((event, i) => (
                          <div className="timeline-row" key={event.id || i}>
                            <div className="timeline-icon">
                              {event.kind === "completed" ? (
                                <Check size={14} />
                              ) : (
                                <Terminal size={14} />
                              )}
                            </div>
                            <div>
                              <strong>{event.node.replaceAll("_", " ")}</strong>
                              <Badge>{event.kind}</Badge>
                              <p>
                                {event.data.summary ||
                                  event.data.message ||
                                  (event.data.arguments
                                    ? JSON.stringify(event.data.arguments)
                                    : "Persisted event")}
                              </p>
                              {event.data.evidence_ids?.map((id) => (
                                <button
                                  className="citation"
                                  key={id}
                                  onClick={() => void openEvidence(id)}
                                >
                                  {id.slice(0, 8)} <PanelRightOpen size={12} />
                                </button>
                              ))}
                            </div>
                            <span className="small muted">
                              {event.duration_ms === null
                                ? "Not measured"
                                : `${event.duration_ms} ms`}
                            </span>
                          </div>
                        ))}
                      </div>
                      <h3 className="lower">Frozen corpus</h3>
                      {run.manifest.map((p) => (
                        <div className="manifest-row" key={p.version_id}>
                          <FileText size={18} />
                          <div>
                            <strong>{p.title}</strong>
                            <p className="mono small">
                              Version {p.version_id}
                              <br />
                              SHA-256 {p.sha256}
                              <br />
                              {p.processing_id}
                            </p>
                          </div>
                        </div>
                      ))}
                      <h3 className="lower">Search record</h3>
                      {result?.queries.map((q, i) => (
                        <p className="query" key={i}>
                          <Search size={14} />
                          {q}
                        </p>
                      ))}
                      {result?.coverage.map((c, i) => (
                        <p className="muted" key={i}>
                          {c}
                        </p>
                      ))}
                    </section>
                  )}
                </>
              ) : (
                <div className="empty hero-empty">
                  <div className="card-icon">
                    <Microscope size={28} />
                  </div>
                  <h2>Start with papers. Follow the evidence.</h2>
                  <p>
                    Create a collection, ingest PDFs, and investigate a focused
                    question.
                    <br />
                    Or explore an original synthetic example without services or
                    an API key.
                  </p>
                  <div className="inline">
                    <button
                      className="button primary"
                      disabled={!!readOnly}
                      onClick={() => setScreen("library")}
                    >
                      Open collection library <ArrowRight size={15} />
                    </button>
                    <button className="button" onClick={() => setExample(true)}>
                      Explore example
                    </button>
                  </div>
                </div>
              )}
            </>
          )}

          {screen === "library" && (
            <section>
              {!readOnly && (
                <form
                  className="inline create-collection"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void action(async () => {
                      const c = await api("/collections", {
                        method: "POST",
                        body: JSON.stringify({ name: collectionName, scope }),
                      });
                      setCollections((cs) => [c, ...cs]);
                      setCollection(c.id);
                      setCollectionName("");
                    });
                  }}
                >
                  <label className="sr-only" htmlFor="collection-name">
                    New collection name
                  </label>
                  <input
                    id="collection-name"
                    value={collectionName}
                    maxLength={150}
                    required
                    placeholder="Name a new collection"
                    onChange={(e) => setCollectionName(e.target.value)}
                  />
                  <button className="button" disabled={busy}>
                    <Plus size={15} />
                    Create collection
                  </button>
                </form>
              )}
              <div className="section-heading">
                <h3>Collection documents</h3>
                <select
                  aria-label="Selected collection"
                  value={collection}
                  onChange={(e) => setCollection(e.target.value)}
                >
                  <option value="" disabled>
                    Select a collection
                  </option>
                  {collections.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
              {!readOnly && (
                <form
                  className="upload-area"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const form = e.currentTarget;
                    const values = new FormData(form);
                    void action(async () => {
                      await api(`/collections/${collection}/papers`, {
                        method: "POST",
                        body: values,
                      });
                      form.reset();
                      setPapers(await api(`/collections/${collection}/papers`));
                    });
                  }}
                >
                  <Upload size={25} />
                  <div>
                    <strong>Add a digitally generated PDF</strong>
                    <p>
                      English embedded text · OCR disabled · default 20 MB limit
                      · parsed locally
                    </p>
                  </div>
                  <label>
                    Paper title
                    <input
                      name="title"
                      required
                      maxLength={200}
                      placeholder="Use the same title to add a new version"
                    />
                  </label>
                  <label>
                    PDF file
                    <input
                      name="file"
                      type="file"
                      accept="application/pdf"
                      required
                    />
                  </label>
                  <button
                    className="button primary"
                    disabled={!collection || busy}
                  >
                    Queue ingestion
                  </button>
                </form>
              )}
              {example
                ? run?.manifest.map((p, i) => (
                    <article className="paper-card" key={p.version_id}>
                      <FileText size={24} />
                      <div>
                        <h3>{p.title}</h3>
                        <p className="mono small muted">
                          Original synthetic fixture · {p.sha256.slice(0, 16)}…
                        </p>
                      </div>
                      <Badge>Example source</Badge>
                      <button
                        className="button"
                        onClick={() =>
                          void openEvidence(run.result!.evidence[i].id)
                        }
                      >
                        Inspect source <ChevronRight size={14} />
                      </button>
                    </article>
                  ))
                : papers.map((p) => (
                    <article className="paper-card" key={p.id}>
                      <FileText size={24} />
                      <div>
                        <h3>{p.title}</h3>
                        <p className="mono small muted">
                          {p.sha256.slice(0, 16)}… · {p.processing_id}
                        </p>
                        {p.error && <p className="error-text">{p.error}</p>}
                        {p.warnings.map((w, i) => (
                          <p className="small muted" key={i}>
                            {w}
                          </p>
                        ))}
                      </div>
                      <Badge
                        tone={
                          p.status === "ready"
                            ? "success"
                            : p.status === "failed"
                              ? "danger"
                              : ""
                        }
                      >
                        {p.status}
                      </Badge>
                    </article>
                  ))}
              {!example && !papers.length && (
                <div className="empty">
                  <BookOpen size={28} />
                  <h3>No papers in this collection yet.</h3>
                  <p>
                    Each paper keeps its original bytes, content hash, and
                    processing version.
                  </p>
                </div>
              )}
            </section>
          )}

          {screen === "setup" && (
            <form
              className="setup-form"
              onSubmit={(e) => {
                e.preventDefault();
                void action(async () => {
                  const r = await api("/runs", {
                    method: "POST",
                    body: JSON.stringify({
                      collection_id: collection,
                      question,
                      scope,
                      provider,
                      mode,
                      budget,
                    }),
                  });
                  setRun(r);
                  setScreen("workspace");
                  setTab("Activity & scope");
                });
              }}
            >
              <div className="setup-main">
                <label>
                  Research question
                  <textarea
                    required
                    minLength={10}
                    maxLength={2000}
                    rows={3}
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                  />
                  <small>
                    Focused enough to compare concrete methods, conditions, and
                    evidence.
                  </small>
                </label>
                <label>
                  Research scope
                  <textarea
                    maxLength={3000}
                    rows={2}
                    value={scope}
                    onChange={(e) => setScope(e.target.value)}
                  />
                </label>
                <label>
                  Collection
                  <select
                    required
                    value={collection}
                    onChange={(e) => setCollection(e.target.value)}
                  >
                    <option value="" disabled>
                      Choose a collection with ready papers
                    </option>
                    {collections.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Workflow
                  <select
                    value={mode}
                    onChange={(e) => setMode(e.target.value)}
                  >
                    {Object.entries(modes).map(([v, l]) => (
                      <option value={v} key={v}>
                        {l}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Provider
                  <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                  >
                    <option value="fixture">
                      Deterministic fixture · not real research
                    </option>
                    <option
                      value="gemini"
                      disabled={!health?.gemini_configured}
                    >
                      Gemini · requires server key & free-tier acknowledgement
                    </option>
                  </select>
                </label>
                {provider === "fixture" && (
                  <p className="notice fixture">
                    Fixture runs test the software workflow. They do not assess
                    real scientific support or novelty.
                  </p>
                )}
                <button
                  className="button primary"
                  disabled={!!readOnly || !collection || busy}
                >
                  Submit investigation <ArrowRight size={16} />
                </button>
                <p className="small muted">
                  The request returns a run ID immediately. Your laptop worker
                  handles the investigation.
                </p>
              </div>
              <aside className="budget-card">
                <h3>Bound the work.</h3>
                <p className="muted">
                  Application limits, independent of provider quotas. No paid
                  fallback.
                </p>
                {Object.entries(budget).map(([key, value]) => (
                  <label key={key}>
                    {key.replaceAll("_", " ")}
                    <input
                      type="number"
                      required
                      min={
                        key === "max_followups"
                          ? 0
                          : key === "max_tokens"
                            ? 1000
                            : key === "max_output_tokens"
                              ? 256
                              : 1
                      }
                      max={
                        key === "max_tokens"
                          ? 100000
                          : key === "max_output_tokens"
                            ? 4000
                            : key === "review_rounds"
                              ? 1
                              : key === "max_followups"
                                ? 3
                                : key === "paper_diversity"
                                  ? 10
                                  : key === "max_tool_calls"
                                    ? 30
                                    : 20
                      }
                      value={value}
                      onChange={(e) =>
                        setBudget((b) => ({
                          ...b,
                          [key]: Number(e.target.value),
                        }))
                      }
                    />
                  </label>
                ))}
                <small>
                  LLM concurrency is one. A quota pause requires explicit
                  resume. Token reservations are conservative ceilings, not
                  measured usage.
                </small>
              </aside>
            </form>
          )}

          {screen === "retrieval" && (
            <section>
              <form
                className="search-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  void action(async () => {
                    if (example) {
                      setHits(run?.result?.evidence || []);
                    } else {
                      setHits(
                        await api(
                          `/collections/${collection}/search?q=${encodeURIComponent(query)}&k=8`,
                        ),
                      );
                    }
                  });
                }}
              >
                <Search size={19} />
                <label className="sr-only" htmlFor="search">
                  Passage search
                </label>
                <input
                  id="search"
                  required
                  maxLength={2000}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search your selected collection"
                />
                <button
                  className="button primary"
                  disabled={!collection || busy}
                >
                  {example ? "Inspect example passages" : "Search passages"}
                  <ArrowRight size={15} />
                </button>
              </form>
              <p className="muted small">
                {example
                  ? "Static source exploration; live keyword/vector rankings require local PostgreSQL."
                  : "PostgreSQL full-text rank + exact cosine similarity, reciprocal rank fusion. Ranks are not confidence probabilities."}
              </p>
              <div className="section-heading">
                <h3>Source passages</h3>
                <span className="muted small">{hits.length} results</span>
              </div>
              {hits.map((p) => (
                <article className="retrieval-card" key={p.id}>
                  <div className="card-top">
                    <span className="small muted">
                      {p.title} <span className="separator">/</span> PAGE{" "}
                      {p.page}
                    </span>
                    {!example && (
                      <span className="rank-tags">
                        Keyword #{p.keyword_rank ?? "—"}{" "}
                        <span>Vector #{p.vector_rank ?? "—"}</span> RRF #
                        {p.fused_rank}
                      </span>
                    )}
                  </div>
                  <h3>{p.heading}</h3>
                  <p>{p.text}</p>
                  <button
                    className="citation"
                    onClick={() => void openEvidence(p.id)}
                  >
                    <Link2 size={13} />
                    Inspect original evidence <ChevronRight size={13} />
                  </button>
                </article>
              ))}
              {!hits.length && (
                <div className="empty">
                  <Search size={25} />
                  <h3>Find a passage, inspect the source.</h3>
                  <p>
                    Search misses describe this corpus, not the whole
                    literature.
                  </p>
                </div>
              )}
            </section>
          )}

          {screen === "history" && (
            <section>
              <div className="section-heading">
                <h3>Saved investigations</h3>
                <Badge>{history.length} runs</Badge>
              </div>
              {history.map((r) => (
                <button
                  className="history-row"
                  key={r.id}
                  onClick={() => {
                    if (example) {
                      setScreen("workspace");
                      return;
                    }
                    void action(async () => {
                      setRun(await api(`/runs/${r.id}`));
                      setScreen("workspace");
                    });
                  }}
                >
                  <span className="history-icon">
                    <Microscope size={18} />
                  </span>
                  <div>
                    <strong>{r.question}</strong>
                    <p>
                      {r.provider === "fixture" ? "SYNTHETIC FIXTURE · " : ""}
                      {modes[r.mode]} · {date(r.created_at)}
                    </p>
                  </div>
                  <Badge tone={r.status === "complete" ? "success" : ""}>
                    {r.status.replaceAll("_", " ")}
                  </Badge>
                  <ChevronRight size={17} />
                </button>
              ))}
              {!history.length && (
                <div className="empty">
                  Your saved investigations will appear here.
                </div>
              )}
            </section>
          )}
          {!example && (
            <details className="owner-access">
              <summary>Owner access</summary>
              <p className="muted small">
                If the private API requires an owner token, enter it here. Kept
                in memory for this tab only.
              </p>
              <form
                className="inline"
                onSubmit={(e) => {
                  e.preventDefault();
                  setOwnerToken(token);
                  setRevision((r) => r + 1);
                }}
              >
                <label className="sr-only" htmlFor="owner-token">
                  Owner token
                </label>
                <input
                  id="owner-token"
                  type="password"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  autoComplete="off"
                />
                <button className="button">Connect</button>
              </form>
            </details>
          )}
          <footer>
            <span>
              <Layers3 size={13} />
              Research Gap Investigator
            </span>
            <span>Inspectable evidence. Provisional conclusions.</span>
          </footer>
        </main>
      </div>
      {evidence && (
        <div
          className="drawer-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setEvidence(null);
          }}
        >
          <div
            className="evidence-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="evidence-title"
            tabIndex={-1}
            ref={dialog}
          >
            <div className="drawer-header">
              <div className="eyebrow">
                <Link2 size={14} /> SOURCE EVIDENCE
              </div>
              <button
                aria-label="Close evidence"
                className="icon-button"
                onClick={() => setEvidence(null)}
              >
                <X size={20} />
              </button>
            </div>
            <h2 id="evidence-title">{evidence.title}</h2>
            <div className="inline">
              <Badge>Page {evidence.page}</Badge>
              <Badge>
                {evidence.boxes.length
                  ? "Source regions available"
                  : "Text & page fallback"}
              </Badge>
            </div>
            <Suspense
              fallback={
                <p role="status" className="muted">
                  Loading PDF viewer…
                </p>
              }
            >
              <PdfPreview passage={evidence} />
            </Suspense>
            <h3>Exact stored passage</h3>
            <blockquote className="source-text">{evidence.text}</blockquote>
            <p className="muted small">
              {evidence.boxes.length
                ? "Highlights show original parser regions, which may cover more than the quoted words."
                : "Extraction coordinates are unavailable. The original page and exact stored text are shown; no bounding boxes have been invented."}
            </p>
            <dl className="source-details">
              <dt>Heading</dt>
              <dd>{evidence.heading}</dd>
              <dt>Evidence ID</dt>
              <dd>{evidence.id}</dd>
              <dt>Document version</dt>
              <dd>{evidence.version_id}</dd>
              <dt>Source item IDs</dt>
              <dd>{evidence.item_ids.join(", ")}</dd>
            </dl>
            {neighbors.length > 1 && (
              <>
                <h3>Surrounding context</h3>
                {neighbors
                  .filter((p) => p.id !== evidence.id)
                  .map((p) => (
                    <div className="neighbor" key={p.id}>
                      <Badge>Page {p.page}</Badge>
                      <p>{p.text}</p>
                    </div>
                  ))}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
