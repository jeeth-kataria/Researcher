"""Export exactly the persisted evidence-backed state, with explicit scope limits."""


def render_report(run, state):
    lines = [
        "# Research Gap Investigator",
        "",
        f"**Provenance: {run['provenance']}**",
        "",
        f"Question: {run['question']}",
        f"Scope: {run['scope']}",
        f"Mode: {run['mode']} | Model: {run['model']}",
        "",
        "Coverage is limited to the frozen uploaded corpus. No external discovery was performed.",
        "Candidate gaps are provisional, not novelty verdicts. Human scientific review is required.",
        "",
        "## Frozen corpus",
    ]
    for paper in run["manifest"]:
        lines.append(
            f"- {paper['title']} — version `{paper['version_id']}`, SHA-256 `{paper['sha256']}`, processing `{paper['processing_id']}`"
        )
    lines.extend(["", "## Search and coverage record"])
    for query in state.get("queries", []):
        lines.append(f"- Searched: {query}")
    for record in state.get("coverage", []):
        lines.append(f"- {record}")
    lines += [
        "",
        "## Literature matrix",
        "Missing values are unknown; results are not automatically comparable.",
        "",
        "| Paper | Methods | Datasets | Baselines | Metrics | Conditions | Results | Limitations | Evidence |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    def clean(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    for row in state.get("matrix", []):
        title = next(
            (p["title"] for p in run["manifest"] if str(p["paper_id"]) == str(row["paper_id"])),
            row["paper_id"],
        )
        cells = [title] + [
            row.get(k, "unknown")
            for k in ("methods", "datasets", "baselines", "metrics", "conditions", "results", "limitations")
        ]
        cells.append(
            ", ".join(f"[{c['evidence_id']}](#e-{c['evidence_id']})" for c in row.get("citations", []))
        )
        lines.append("| " + " | ".join(clean(v) for v in cells) + " |")
    lines += ["", "## Findings and support review"]
    judgments = {r["claim_index"]: r for r in state.get("support_reviews", [])}
    for i, claim in enumerate(state.get("claims", [])):
        support = judgments.get(
            i, {"judgment": "insufficient", "reason": "No separate support judgment available"}
        )
        lines += [
            f"- **{claim['category']} / {support['judgment']}**: {claim['text']}",
            f"  Review: {support['reason']}",
        ]
        for c in claim["citations"]:
            lines.append(f"  [{c['evidence_id']}](#e-{c['evidence_id']}): “{c['quote']}”")
    lines += ["", "## Candidate gaps, objections and decisions"]
    for gap in state.get("gaps", []):
        review = next((r for r in state.get("reviews", []) if r["gap_id"] == gap["id"]), None)
        lines += [
            f"### {gap['id']}: {gap['description']}",
            f"Type: {gap['kind']}",
            f"Significance: {gap['significance']}",
            f"Concerns: {gap['concerns']}",
        ]
        for c in gap.get("citations", []):
            lines.append(f"Support [{c['evidence_id']}](#e-{c['evidence_id']}): “{c['quote']}”")
        if review:
            lines += [
                f"Disposition: **{review['disposition']}** — {review['rationale']}",
                f"Unresolved: {review['unresolved']}",
            ]
            for c in review["counterevidence"]:
                lines.append(f"Counterevidence [{c['evidence_id']}](#e-{c['evidence_id']}): “{c['quote']}”")
        else:
            lines.append("Disposition: **insufficient** — baseline did not conduct a skeptical review.")
    lines += ["", "## Experiment proposals (not executed)"]
    if not state.get("experiments"):
        lines.append("No experiment proposed for rejected or insufficiently supported candidates.")
    for exp in state.get("experiments", []):
        for key, value in exp.items():
            lines.append(f"- {key}: {value}")
    lines += [
        "",
        "## Limitations",
        "Exact citation matching checks provenance, not semantic support.",
        "A model reviewer is not independent scientific verification. No percentage confidence is assigned.",
        "Searches are bounded and corpus-only. Missing evidence and incompatible settings remain unresolved.",
        "",
        "## References and inspectable passages",
    ]
    for p in state.get("evidence", []):
        lines += [
            f'<a id="e-{p["id"]}"></a>',
            f"### {p['title']} — page {p['page']}",
            f"Evidence `{p['id']}` | version `{p['version_id']}` | {p['heading']}",
            f"Source items: {p.get('item_ids', [])}",
            "Coordinates available in evidence inspector."
            if p.get("boxes")
            else "Coordinates unavailable; exact text/page fallback.",
            f"> {p['text']}",
            "",
        ]
    return "\n".join(lines)
