"""Deterministic provenance checks. These do not establish semantic entailment."""

from .schemas import RoleOutput


def normalize(text):
    return " ".join(text.split())


def validate_output(output: RoleOutput, passages, manifest, prior=None):
    allowed = {str(x["version_id"]) for x in manifest}
    by_id = {str(p["id"]): p for p in passages}
    paper_ids = {str(x["paper_id"]) for x in manifest}

    def citation_check(citation):
        source = by_id.get(str(citation.evidence_id))
        if not source or str(source["version_id"]) not in allowed:
            raise ValueError("Citation is not in retrieved, frozen run evidence")
        if normalize(citation.quote) not in normalize(source["text"]):
            raise ValueError("Quotation does not map to stored source text")

    for claim in output.claims:
        for citation in claim.citations:
            citation_check(citation)
        # A generator cannot self-award semantic support; reviewer sets this later.
        if claim.support != "pending":
            raise ValueError("Claim support must be pending until the support review")
    for row in output.matrix:
        if str(row.paper_id) not in paper_ids:
            raise ValueError("Matrix paper outside frozen manifest")
        known = [
            getattr(row, key)
            for key in ("methods", "datasets", "baselines", "metrics", "conditions", "results", "limitations")
        ]
        if any(value != "unknown" for value in known) and not row.citations:
            raise ValueError("Known matrix values require source citations")
        for citation in row.citations:
            citation_check(citation)
            if str(by_id[str(citation.evidence_id)]["paper_id"]) != str(row.paper_id):
                raise ValueError("Matrix citation belongs to a different paper")
    ids = [gap.id for gap in output.gaps]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate candidate IDs")
    for gap in output.gaps:
        for citation in gap.citations:
            citation_check(citation)
        if gap.kind == "candidate_gap" and not gap.citations:
            raise ValueError("Candidate gap needs evidence; otherwise mark unresolved")
    for review in output.reviews:
        for citation in review.counterevidence:
            citation_check(citation)
        if review.disposition == "contradicted" and not review.counterevidence:
            raise ValueError("Contradiction requires supporting counterevidence")
    if prior:
        gaps = {g["id"] for g in prior.get("gaps", [])}
        reviews = {r["gap_id"]: r for r in prior.get("reviews", [])}
        seen_reviews = set()
        for review in output.reviews:
            if review.gap_id not in gaps or review.gap_id in seen_reviews:
                raise ValueError("Unknown or duplicate review gap ID")
            seen_reviews.add(review.gap_id)
        for experiment in output.experiments:
            if (
                experiment.gap_id not in gaps
                or reviews.get(experiment.gap_id, {}).get("disposition") != "survived"
            ):
                raise ValueError("Experiments require a candidate that survived review")
        seen_claims = set()
        for support in output.support_reviews:
            if support.claim_index >= len(prior.get("claims", [])) or support.claim_index in seen_claims:
                raise ValueError("Unknown or duplicate support-review claim index")
            seen_claims.add(support.claim_index)
    return output
