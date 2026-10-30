"""Comparable run evaluation. Deterministic fixtures never establish research quality."""

import argparse
import hashlib
import json
import time
from pathlib import Path
import httpx
from .evidence import normalize
from .provider import Fixture

ROOT = Path(__file__).resolve().parents[2]


def ratio(numerator, denominator):
    return {
        "value": numerator / denominator if denominator else None,
        "numerator": numerator,
        "denominator": denominator,
    }


def metrics(run, relevant_snippets, human=None):
    state = run["result"]
    passages = {str(p["id"]): p for p in state.get("evidence", [])}
    allowed = {m["version_id"] for m in run["manifest"]}
    # Evaluate the initial retrieval, rather than counting later followups as initial recall@k.
    initial_ids = run.get("initial_retrieval_ids", list(passages))
    texts = [passages[i]["text"] for i in initial_ids if i in passages]
    recalled = sum(
        any(normalize(label).lower() in normalize(t).lower() for t in texts) for label in relevant_snippets
    )
    claims = state.get("claims", [])
    citations = [c for claim in claims for c in claim.get("citations", [])]
    correct = sum(
        c["evidence_id"] in passages
        and passages[c["evidence_id"]]["version_id"] in allowed
        and normalize(c["quote"]) in normalize(passages[c["evidence_id"]]["text"])
        for c in citations
    )
    judgments = human or {}
    judged = []
    for claim in claims:
        key = hashlib.sha256(claim["text"].encode()).hexdigest()
        if key in judgments.get("claim_support", {}):
            judged.append(judgments["claim_support"][key])
    gap_judgments = list(judgments.get("false_candidate_gaps", {}).values())
    return {
        "draft_retrieval_recall_at_k": ratio(recalled, len(relevant_snippets)),
        "citation_correctness_structural_only": ratio(correct, len(citations)),
        "human_factual_support": ratio(sum(j is True for j in judged), len(judged)),
        "human_false_candidate_gap_rate": ratio(sum(j is True for j in gap_judgments), len(gap_judgments)),
        "unjudged_claims": len(claims) - len(judged),
        "candidate_count": len(state.get("gaps", [])),
        "dispositions": {
            d: sum(r["disposition"] == d for r in state.get("reviews", []))
            for d in ("survived", "contradicted", "insufficient")
        },
        "calls": run["calls"],
        "tokens": None if run.get("usage_unknown") else run["tokens"],
    }


def offline(case, mode):
    example = json.loads((ROOT / "frontend/public/examples/run.json").read_text())
    state = {
        "manifest": example["manifest"],
        "evidence": example["result"]["evidence"],
        "queries": [case["question"]],
    }
    roles = (
        ["rag"]
        if mode == "rag"
        else (
            ["single", "review", "experiments"]
            if mode == "single"
            else ["plan", "literature", "methods", "candidates", "review", "experiments"]
        )
    )
    start = time.perf_counter()
    for role in roles:
        output, _, _ = Fixture().generate(role, "", state, 1800)
        dumped = output.model_dump(mode="json")
        for key in ("claims", "matrix", "gaps", "reviews", "support_reviews", "experiments", "coverage"):
            if dumped[key]:
                state[key] = dumped[key]
    elapsed = time.perf_counter() - start
    return {
        **example,
        "mode": mode,
        "question": case["question"],
        "result": state,
        "calls": len(roles),
        "tokens": 0,
        "measured_fixture_function_seconds": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Fixture functions only; no PostgreSQL, no research quality claim",
    )
    parser.add_argument("--collection", help="Existing ready collection UUID; required unless --offline")
    parser.add_argument("--provider", choices=["fixture", "gemini"], default="fixture")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path(".data/evaluation.json"))
    parser.add_argument(
        "--judgments",
        type=Path,
        help="Human-reviewed claim_support hashes / false_candidate_gaps; no self-scores",
    )
    args = parser.parse_args()
    if not args.offline and not args.collection:
        parser.error("--collection is required for actual API/worker evaluation")
    if args.offline and args.provider != "fixture":
        parser.error("Offline evaluation only supports the explicitly synthetic fixture provider")
    cases = json.loads((ROOT / "evaluation/draft_cases.json").read_text())
    human = json.loads(args.judgments.read_text()) if args.judgments else {}
    if args.judgments and human.get("review_status") != "human-reviewed":
        parser.error("Judgments must explicitly attest review_status=human-reviewed")
    output = {
        "provenance": "SYNTHETIC FIXTURE FUNCTIONS ONLY"
        if args.offline
        else f"API/worker {args.provider} runs",
        "annotation_status": cases["annotation_status"],
        "human_judgments_supplied": bool(args.judgments),
        "warning": "Draft relevance labels are not human ground truth. No multi-agent superiority conclusion.",
        "budget": {"max_calls": 10, "max_tokens": 60000, "retrieval_k": 8},
        "results": [],
    }
    import os

    headers = (
        {"Authorization": f"Bearer {os.environ['RGI_OWNER_TOKEN']}"} if os.getenv("RGI_OWNER_TOKEN") else {}
    )
    expected_manifest = None
    with httpx.Client(base_url=args.url, headers=headers, timeout=30) as api:
        for case in cases["cases"]:
            for mode in ("rag", "single", "multi"):
                if args.offline:
                    run = offline(case, mode)
                    elapsed = run["measured_fixture_function_seconds"]
                else:
                    start = time.perf_counter()
                    response = api.post(
                        "/api/runs",
                        json={
                            "collection_id": args.collection,
                            "question": case["question"],
                            "mode": mode,
                            "provider": args.provider,
                            "budget": output["budget"],
                        },
                    )
                    response.raise_for_status()
                    rid = response.json()["id"]
                    deadline = time.monotonic() + 900
                    while time.monotonic() < deadline:
                        response = api.get(f"/api/runs/{rid}")
                        response.raise_for_status()
                        run = response.json()
                        if run["status"] == "complete":
                            break
                        if run["status"] in ("failed", "paused", "waiting_for_quota", "cancelled"):
                            raise SystemExit(
                                f"Run {rid}: {run['status']}; evaluation stopped without fallback"
                            )
                        time.sleep(2)
                    else:
                        raise SystemExit("Evaluation timed out; queued runs remain persisted")
                    elapsed = time.perf_counter() - start
                    events = [
                        e
                        for e in run["events"]
                        if e["node"] == "search_passages" and e["kind"] == "tool_result"
                    ]
                    run["initial_retrieval_ids"] = events[0]["data"]["evidence_ids"] if events else []
                manifest = sorted(m["version_id"] for m in run["manifest"])
                if expected_manifest is not None and manifest != expected_manifest:
                    raise SystemExit("Corpus changed during comparison; rerun with frozen document versions")
                expected_manifest = manifest
                output["results"].append(
                    {
                        "case": case["id"],
                        "mode": mode,
                        "model": run["model"],
                        "manifest": manifest,
                        "latency_seconds": elapsed,
                        "latency_definition": "fixture functions only"
                        if args.offline
                        else "submission-to-completion including queue and polling",
                        "metrics": metrics(run, case["relevant_snippets"], human.get(run["id"], {})),
                    }
                )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"Wrote {args.output}. {output['provenance']}; labels pending human review.")


if __name__ == "__main__":
    main()
