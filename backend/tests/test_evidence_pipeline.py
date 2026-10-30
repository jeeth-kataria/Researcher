import json
from pathlib import Path
from uuid import uuid4
import pytest
from rgi.embeddings import FixtureEmbedder, vector_sql
from rgi.ingest import Item, chunk_items, parse_pdf
from rgi.storage import path_for, store_pdf
from rgi.schemas import RoleOutput, Claim, Citation, MatrixRow, Review, Experiment
from rgi.evidence import validate_output
from rgi.provider import Fixture, retry_after
from rgi.research import validate_role
from rgi.report import render_report

ROOT = Path(__file__).resolve().parents[2]


def test_exact_token_limit_and_provenance():
    enc = FixtureEmbedder()
    item = Item("Token context. " * 1000, 3, "Methods", ["#/texts/1"], [{"page": 3}])
    chunks = list(chunk_items([item], enc))
    assert len(chunks) > 1
    assert all(c["token_count"] <= 420 and enc.count(c["payload"]) <= 512 for c in chunks)
    assert all(
        c["page"] == 3 and c["item_ids"] == ["#/texts/1"] and c["boxes"] == [{"page": 3}] for c in chunks
    )
    assert " ".join(c["text"] for c in chunks) == " ".join(item.text.split())
    with pytest.raises(ValueError, match="window"):
        enc.encode(["word " * 600])


def test_heading_budget_and_invalid_vector():
    chunks = list(chunk_items([Item("Small body.", 1, "header " * 200)], FixtureEmbedder()))
    assert chunks[0]["heading"] == "header " * 200
    assert chunks[0]["payload"].startswith("Document section")
    with pytest.raises(ValueError):
        vector_sql([float("nan")] * 384)


def test_storage_bounds_and_content_hash(isolated_settings):
    first = store_pdf(b"%PDF-1.7\noriginal fixture")
    second = store_pdf(b"%PDF-1.7\noriginal fixture")
    assert first == second
    assert path_for(first[1]).read_bytes().startswith(b"%PDF")
    assert store_pdf(b"%PDF-1.7\nnew version")[0] != first[0]
    with pytest.raises(ValueError, match="Unsafe"):
        path_for("../../secrets")
    with pytest.raises(ValueError, match="Only PDF"):
        store_pdf(b"<html>not pdf</html>")
    with pytest.raises(ValueError, match="exceeds"):
        store_pdf(b"%PDF-" + b"x" * (isolated_settings.max_upload_mb * 1024 * 1024))


def evidence():
    eid, vid, pid = uuid4(), uuid4(), uuid4()
    passage = {
        "id": str(eid),
        "version_id": str(vid),
        "paper_id": str(pid),
        "text": "We studied memory retrieval in a synthetic setting.",
    }
    return passage, [{"version_id": str(vid), "paper_id": str(pid)}]


def test_citation_existence_manifest_and_exact_quote():
    passage, manifest = evidence()
    claim = Claim(
        text="Retrieval was studied.",
        category="finding",
        citations=[Citation(evidence_id=passage["id"], quote="studied memory retrieval")],
    )
    output = RoleOutput(summary="Finding", claims=[claim])
    assert validate_output(output, [passage], manifest)
    with pytest.raises(ValueError, match="frozen"):
        validate_output(output, [passage], [{"version_id": str(uuid4()), "paper_id": str(uuid4())}])
    claim.citations[0].quote = "A fabricated quote that is absent"
    with pytest.raises(ValueError, match="Quotation"):
        validate_output(output, [passage], manifest)


def test_missing_evidence_and_self_awarded_support():
    with pytest.raises(ValueError):
        Claim(text="Unsupported literature fact", category="finding")
    claim = Claim(text="Unknown factual support", category="unsupported")
    assert claim.citations == []
    passage, manifest = evidence()
    claim = Claim(
        text="Self award",
        category="finding",
        support="supported",
        citations=[Citation(evidence_id=passage["id"], quote="studied memory retrieval")],
    )
    with pytest.raises(ValueError, match="pending"):
        validate_output(RoleOutput(summary="test", claims=[claim]), [passage], manifest)


def test_matrix_cannot_use_another_paper():
    passage, manifest = evidence()
    other = {"version_id": str(uuid4()), "paper_id": str(uuid4())}
    output = RoleOutput(
        summary="test",
        matrix=[
            MatrixRow(
                paper_id=other["paper_id"],
                methods="a method",
                citations=[Citation(evidence_id=passage["id"], quote="studied memory retrieval")],
            )
        ],
    )
    with pytest.raises(ValueError, match="different paper"):
        validate_output(output, [passage], manifest + [other])


def test_malformed_outputs_and_injected_tool_rejected():
    with pytest.raises(ValueError):
        RoleOutput.model_validate_json('{"summary":"x","shell":"rm -rf /"}')
    from rgi.tools import SearchInput

    with pytest.raises(ValueError):
        SearchInput(query="okay", k=999)
    with pytest.raises(ValueError):
        SearchInput(query="okay", collection_id=str(uuid4()))


def test_reviewer_must_address_every_candidate_and_claim():
    with pytest.raises(ValueError, match="every candidate"):
        validate_role("review", RoleOutput(summary="abstain"), {"gaps": [{"id": "g1"}], "claims": []})
    with pytest.raises(ValueError, match="every claim"):
        validate_role("review", RoleOutput(summary="abstain"), {"gaps": [], "claims": [{"text": "claim"}]})
    with pytest.raises(ValueError, match="Contradiction"):
        validate_output(
            RoleOutput(
                summary="reject",
                reviews=[
                    Review(
                        gap_id="g", disposition="contradicted", rationale="No evidence", unresolved="unknown"
                    )
                ],
            ),
            [],
            [],
        )


def test_experiment_requires_review_survivor():
    exp = Experiment(
        gap_id="g1",
        hypothesis="proposal",
        baselines="b",
        variables="v",
        datasets="d",
        metrics="m",
        refutation="null effect",
        resources="CPU",
        feasibility="unknown",
    )
    with pytest.raises(ValueError, match="survived"):
        validate_output(
            RoleOutput(summary="test", experiments=[exp]),
            [],
            [],
            {"gaps": [{"id": "g1"}], "reviews": [{"gap_id": "g1", "disposition": "contradicted"}]},
        )


def test_fixture_control_and_explicit_provenance():
    run = json.loads((ROOT / "frontend/public/examples/run.json").read_text())
    state = run["result"]
    review, tokens, _ = Fixture().generate("review", "", state, 1800)
    assert next(r for r in review.reviews if r.gap_id == "control").disposition == "contradicted"
    assert tokens == 0
    assert all(r.judgment == "insufficient" for r in review.support_reviews)
    report = render_report(run, state)
    assert "SYNTHETIC FIXTURE" in report
    assert "not novelty verdicts" in report
    assert "Coordinates unavailable" in report
    assert "refutation" in report
    assert "unknown" in report


def test_retry_after_is_respected():
    from datetime import datetime, timezone

    class Exc:
        response = type("Response", (), {"headers": {"Retry-After": "120"}})()

    before = datetime.now(timezone.utc)
    assert (retry_after(Exc()) - before).total_seconds() >= 119


def test_baseline_real_pdf_extraction():
    pytest.importorskip("pypdf")
    items, artifact = parse_pdf(ROOT / "fixtures/paper-a.pdf", "pypdf")
    assert any("studied memory retrieval" in item.text for item in items)
    assert items[0].page == 1
    assert artifact["warnings"]


def test_processing_configuration_invalidates_identity(isolated_settings, monkeypatch):
    from rgi.ingest import processing_id

    original = processing_id()
    monkeypatch.setattr("rgi.ingest.embedding_identity", lambda: "different-revision-and-preprocessing")
    assert processing_id() != original
