"""Understandable functions first; the graph only schedules these bounded stages."""

import hashlib
import json
from time import monotonic
from typing import TypedDict
from .db import one, connect, json_value
from .jobs import event, fence, check_cancel
from .schemas import RoleOutput
from .provider import provider, SYSTEM, QuotaPause, AmbiguousCall, BudgetExceeded, ConfigurationPause
from .evidence import validate_output
from .tools import Tools
from .report import render_report


class ResearchState(TypedDict, total=False):
    run_id: str
    manifest: list[dict]
    evidence: list[dict]
    queries: list[str]
    coverage: list[str]
    claims: list[dict]
    matrix: list[dict]
    gaps: list[dict]
    reviews: list[dict]
    support_reviews: list[dict]
    experiments: list[dict]
    summary: str
    completed: list[str]


TASKS = {
    "plan": "Lead researcher: refine question/scope, give a bounded corpus-only coverage plan. No factual conclusions yet.",
    "literature": "Literature investigator: record inclusion/exclusion and coverage. Suggest at most configured followup queries. Do not propose gaps.",
    "methods": "Methods analyst: extract per-paper matrix and literature claims with exact quotes. Missing values unknown; preserve conditions. No gaps.",
    "candidates": "Lead researcher: propose scoped candidate gaps or unresolved hypotheses after extraction. Include strongest concerns and source evidence. Never universal novelty.",
    "review": "Skeptical reviewer: actively challenge EVERY candidate using supplied context. Return one review per gap. Contradictions need exact counterevidence. Separately judge semantic support for EVERY prior claim (index-based) with a concise reason. Survived means provisional; when evidence is insufficient abstain.",
    "experiments": "Experiment designer: propose falsifiable experiments ONLY for gap IDs with survived disposition. Include refutation, baselines, variables, metrics, dataset needs and realistic CPU/hardware limits. Proposals only.",
    "single": "Single research agent: extract matrix and claims and propose scoped gaps from supplied evidence. Preserve unknowns. No self-assigned support. May suggest bounded followup queries.",
    "rag": "Ordinary RAG baseline: answer using the supplied retrieved passages and exact citations. No further tool queries. May record candidate hypotheses; do not claim novelty or reviewed status.",
}


def serializable(value):
    return json.loads(json.dumps(value, default=str))


class Investigation:
    def __init__(self, run, job, owner):
        self.run, self.job, self.owner = run, job, owner
        self.tools = Tools(run, job, owner)

    def retrieve(self, state):
        check_cancel(self.run["id"])
        corpus = self.tools.call("list_corpus", {})
        hits = self.tools.call(
            "search_passages",
            {"query": self.run["question"], "k": self.run["config"]["budget"]["retrieval_k"]},
        )
        return {
            "manifest": corpus,
            "evidence": serializable(hits),
            "queries": [self.run["question"]],
            "completed": state.get("completed", []) + ["retrieve"],
        }

    def model_call(self, role, state):
        budget = self.run["config"]["budget"]
        check_cancel(self.run["id"])
        task = TASKS[role]
        if self.run["mode"] == "single" and role in ("review", "experiments"):
            task = (
                "Continue as the SAME single research agent, not an independent worker. "
                "Self-review your prior candidates and every claim with exact counterevidence; abstain where unsure. "
                if role == "review"
                else "Continue as the SAME single research agent. Propose falsifiable experiments only for candidates "
                "that survived your explicit self-review. State refutation and hardware limits. "
            )
        data = {
            "question": self.run["question"],
            "scope": self.run["scope"],
            "task": task,
            "max_followups": budget["max_followups"],
            "data": {k: v for k, v in state.items() if k not in ("run_id", "completed")},
        }
        prompt = json.dumps(data, ensure_ascii=False, default=str)
        identity = f"{self.run['provider']}:{self.run['model']}:{self.run['config']['prompt_version']}:role-v1:{role}:output-{budget['max_output_tokens']}"
        reusable_key = hashlib.sha256((identity + prompt).encode()).hexdigest()
        key = hashlib.sha256((str(self.run["id"]) + reusable_key).encode()).hexdigest()
        with connect() as conn:
            fence(conn, self.job["id"], self.owner)
            cached = conn.execute("SELECT * FROM llm_calls WHERE cache_key=?", (key,)).fetchone()
            if cached and cached["status"] == "complete":
                return RoleOutput.model_validate(cached["response"])
            if cached and cached["status"] in ("pending", "uncertain"):
                raise AmbiguousCall(
                    "Worker stopped around a model call. Explicit duplicate-call acknowledgement required."
                )
            extraction = (
                conn.execute(
                    "SELECT payload FROM extraction_cache WHERE cache_key=?", (reusable_key,)
                ).fetchone()
                if role == "methods"
                else None
            )
            if extraction:
                event(conn, self.run["id"], role, "cache_hit", {"cache_key": reusable_key})
                return RoleOutput.model_validate(extraction["payload"])
            generator = provider(self.run["provider"], self.run["model"])
            # Construct/configure before recording call intent: a missing local key
            # is a known no-call failure and must not trigger duplicate-call warnings.
            # UTF-8 byte count + schema/system bytes is a conservative token ceiling,
            # not a token-usage measurement. Reconcile from provider usage afterward.
            reserve = (
                0
                if self.run["provider"] == "fixture"
                else (
                    len((prompt + SYSTEM + json.dumps(RoleOutput.model_json_schema())).encode())
                    + budget["max_output_tokens"]
                    + 256
                )
            )
            reservation = conn.execute(
                """UPDATE runs SET calls=calls+1,reserved_tokens=reserved_tokens+?,
                updated_at=now() WHERE id=? AND calls<? AND tokens+reserved_tokens+?<=? RETURNING id""",
                (reserve, self.run["id"], budget["max_calls"], reserve, budget["max_tokens"]),
            ).fetchone()
            if not reservation:
                raise BudgetExceeded(
                    "Application call/token budget reached; increase limits explicitly to resume"
                )
            conn.execute(
                """INSERT INTO llm_calls(cache_key,run_id,role,status) VALUES (?,?,?,'pending')
                ON CONFLICT(cache_key) DO UPDATE SET status='pending',updated_at=now()""",
                (key, self.run["id"], role),
            )
            event(conn, self.run["id"], role, "started", {"reserved_token_ceiling": reserve})
        start = monotonic()
        try:
            output, used, usage = generator.generate(role, prompt, state, budget["max_output_tokens"])
            validate_output(output, state.get("evidence", []), self.run["manifest"], state)
            validate_role(role, output, state)
        except (QuotaPause, ConfigurationPause):
            with connect() as conn:
                fence(conn, self.job["id"], self.owner)
                conn.execute(
                    "UPDATE llm_calls SET status='quota_or_config_rejected',updated_at=now() WHERE cache_key=?",
                    (key,),
                )
                conn.execute(
                    "UPDATE runs SET reserved_tokens=reserved_tokens-? WHERE id=?",
                    (reserve, self.run["id"]),
                )
            raise
        except Exception:
            with connect() as conn:
                fence(conn, self.job["id"], self.owner)
                conn.execute(
                    "UPDATE llm_calls SET status='uncertain',updated_at=now() WHERE cache_key=?", (key,)
                )
                conn.execute("UPDATE runs SET usage_unknown=true WHERE id=?", (self.run["id"],))
            raise AmbiguousCall(
                "Provider call outcome or response validation is uncertain; explicit retry acknowledgement required"
            ) from None
        with connect() as conn:
            fence(conn, self.job["id"], self.owner)
            actual = reserve if used is None else used
            conn.execute(
                """UPDATE runs SET reserved_tokens=reserved_tokens-?,tokens=tokens+?,
                usage_unknown=usage_unknown OR ?,updated_at=now() WHERE id=?""",
                (reserve, actual, used is None, self.run["id"]),
            )
            conn.execute(
                """UPDATE llm_calls SET status='complete',response=?,input_tokens=?,
                output_tokens=?,updated_at=now() WHERE cache_key=?""",
                (
                    json_value(output.model_dump(mode="json")),
                    usage["input_tokens"],
                    usage["output_tokens"],
                    key,
                ),
            )
            if role == "methods":
                conn.execute(
                    "INSERT INTO extraction_cache(cache_key,payload) VALUES (?,?) ON CONFLICT DO NOTHING",
                    (reusable_key, json_value(output.model_dump(mode="json"))),
                )
            event(
                conn,
                self.run["id"],
                role,
                "completed",
                {
                    "summary": output.summary,
                    "usage": usage,
                    "evidence_ids": [str(c.evidence_id) for c in output.claims for c in c.citations],
                },
                int((monotonic() - start) * 1000),
            )
        return output

    def role(self, role, state):
        output = self.model_call(role, state)
        delta = {"completed": state.get("completed", []) + [role], "summary": output.summary}
        # Stage-specific fields prevent a role overwriting another role's decisions.
        fields = {
            "plan": ("coverage",),
            "literature": ("coverage",),
            "methods": ("claims", "matrix"),
            "candidates": ("gaps",),
            "review": ("reviews", "support_reviews"),
            "experiments": ("experiments",),
            "single": ("claims", "matrix", "gaps", "coverage"),
            "rag": ("claims", "matrix", "gaps", "coverage"),
        }[role]
        dumped = output.model_dump(mode="json")
        for field in fields:
            delta[field] = dumped[field]
        if role in ("literature", "single"):
            evidence = {str(p["id"]): p for p in state.get("evidence", [])}
            queries = list(state.get("queries", []))
            for query in output.queries[: self.run["config"]["budget"]["max_followups"]]:
                if query in queries:
                    continue
                hits = self.tools.call(
                    "search_passages", {"query": query, "k": self.run["config"]["budget"]["retrieval_k"]}
                )
                for hit in serializable(hits):
                    evidence[str(hit["id"])] = hit
                queries.append(query)
            delta.update(evidence=list(evidence.values()), queries=queries)
        # Review receives neighboring source context, not just generated summaries.
        if role == "candidates":
            evidence = {str(p["id"]): p for p in state.get("evidence", [])}
            queries = list(state.get("queries", []))
            # A deterministic counter-search gives the reviewer an independent retrieval
            # opportunity. It is a bounded search, not independent scientific verification.
            used_tools = one("SELECT tool_calls FROM runs WHERE id=?", (self.run["id"],))["tool_calls"]
            for gap in dumped["gaps"][: self.run["config"]["budget"]["max_followups"]]:
                if used_tools >= self.run["config"]["budget"]["max_tool_calls"]:
                    break
                query = gap["description"][:1500]
                hits = self.tools.call(
                    "search_passages", {"query": query, "k": self.run["config"]["budget"]["retrieval_k"]}
                )
                for hit in serializable(hits):
                    evidence[hit["id"]] = hit
                queries.append(query)
                used_tools += 1
            delta["queries"] = queries
            refs = list(dict.fromkeys(c["evidence_id"] for g in dumped["gaps"] for c in g["citations"]))
            remaining = one("SELECT tool_calls FROM runs WHERE id=?", (self.run["id"],))["tool_calls"]
            available = self.run["config"]["budget"]["max_tool_calls"] - remaining
            for evidence_id in refs[: max(0, available)]:
                context_result = serializable(self.tools.call("read_context", {"evidence_id": evidence_id}))
                original = context_result["passage"]
                for neighbor in context_result["neighbors"]:
                    if neighbor["id"] not in evidence:
                        evidence[neighbor["id"]] = {**original, **neighbor}
            delta["evidence"] = list(evidence.values())
        with connect() as conn:
            fence(conn, self.job["id"], self.owner)
            conn.execute(
                """INSERT INTO artifacts(run_id,role,payload) VALUES (?,?,?)
                ON CONFLICT(run_id,role) DO UPDATE SET payload=excluded.payload""",
                (self.run["id"], role, json_value(dumped)),
            )
        return delta

    def finalize(self, state):
        check_cancel(self.run["id"])
        result = serializable(state)
        report = render_report(self.run, result)
        with connect() as conn:
            fence(conn, self.job["id"], self.owner)
            conn.execute(
                "UPDATE runs SET result=?,report=?,updated_at=now() WHERE id=?",
                (json_value(result), report, self.run["id"]),
            )
            event(
                conn,
                self.run["id"],
                "report",
                "completed",
                {"format": "markdown", "provenance": self.run["provenance"]},
            )
        return {"completed": state.get("completed", []) + ["report"]}


def validate_role(role, output, state):
    """Enforce the graph's dependency contract, independent of model obedience."""
    if role not in ("candidates", "single", "rag") and output.gaps:
        raise ValueError("Only orchestrator/baselines may propose candidates")
    if role != "review" and (output.reviews or output.support_reviews):
        raise ValueError("Only skeptical reviewer may submit judgments")
    if role != "experiments" and output.experiments:
        raise ValueError("Only experiment designer may propose experiments")
    if role == "review":
        if {r.gap_id for r in output.reviews} != {g["id"] for g in state.get("gaps", [])}:
            raise ValueError("Reviewer must address every candidate")
        if {r.claim_index for r in output.support_reviews} != set(range(len(state.get("claims", [])))):
            raise ValueError("Reviewer must address every claim")


def build_graph(investigation, checkpointer):
    from langgraph.graph import StateGraph, START, END

    builder = StateGraph(ResearchState)
    builder.add_node("retrieve", investigation.retrieve)
    mode = investigation.run["mode"]
    roles = (
        ["rag"]
        if mode == "rag"
        else (
            ["single", "review", "experiments"]
            if mode == "single"
            else ["plan", "literature", "methods", "candidates", "review", "experiments"]
        )
    )
    previous = "retrieve"
    builder.add_edge(START, previous)
    for role in roles:
        node_name = f"stage_{role}"
        builder.add_node(node_name, lambda state, role=role: investigation.role(role, state))
        builder.add_edge(previous, node_name)
        previous = node_name
    builder.add_node("report", investigation.finalize)
    builder.add_edge(previous, "report")
    builder.add_edge("report", END)
    return builder.compile(checkpointer=checkpointer)


def execute(run, job, owner):
    from .db import checkpoints, run_lock

    check_cancel(run["id"])
    # The file lock spans each node return and subsequent checkpoint commit.
    # Lease fencing separately prevents a stale worker writing application data.
    with run_lock(run["id"]):
        with connect() as conn:
            fence(conn, job["id"], owner)
            conn.execute(
                "UPDATE runs SET status='running',error=NULL,updated_at=now() WHERE id=?", (run["id"],)
            )
        with checkpoints() as saver:
            graph = build_graph(Investigation(run, job, owner), saver)
            config = {"configurable": {"thread_id": str(run["id"])}, "recursion_limit": 20}
            snapshot = graph.get_state(config)
            if snapshot.values and not snapshot.next:
                return snapshot.values
            initial = None if snapshot.values else {"run_id": str(run["id"]), "manifest": run["manifest"]}
            return graph.invoke(initial, config=config)
