from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CollectionInput(Strict):
    name: str = Field(min_length=1, max_length=150)
    scope: str = Field(default="Agent memory and long-context reliability", max_length=3000)


class Budget(Strict):
    max_calls: int = Field(default=10, ge=1, le=20)
    max_tokens: int = Field(default=60000, ge=1000, le=100000)
    max_output_tokens: int = Field(default=1800, ge=256, le=4000)
    max_tool_calls: int = Field(default=12, ge=1, le=30)
    max_followups: int = Field(default=2, ge=0, le=3)
    review_rounds: int = Field(default=1, ge=1, le=1)
    retrieval_k: int = Field(default=8, ge=1, le=20)
    paper_diversity: int = Field(default=3, ge=1, le=10)


class RunInput(Strict):
    collection_id: UUID
    question: str = Field(min_length=10, max_length=2000)
    scope: str = Field(default="Uploaded corpus only", max_length=3000)
    mode: Literal["rag", "single", "multi"] = "multi"
    provider: Literal["fixture", "gemini"] = "fixture"
    budget: Budget = Field(default_factory=Budget)


class Citation(Strict):
    evidence_id: UUID
    quote: str = Field(min_length=5, max_length=2000)


class Claim(Strict):
    text: str = Field(min_length=1, max_length=2000)
    category: Literal["finding", "author_limitation", "inference", "unsupported"]
    citations: list[Citation] = Field(default_factory=list, max_length=8)
    support: Literal["pending", "supported", "insufficient", "contradicted"] = "pending"

    @model_validator(mode="after")
    def requires_evidence(self):
        if self.category in ("finding", "author_limitation") and not self.citations:
            raise ValueError("Literature facts need citations; otherwise label unsupported")
        return self


class MatrixRow(Strict):
    paper_id: UUID
    methods: str = "unknown"
    datasets: str = "unknown"
    baselines: str = "unknown"
    metrics: str = "unknown"
    conditions: str = "unknown"
    results: str = "unknown"
    limitations: str = "unknown"
    citations: list[Citation] = Field(default_factory=list, max_length=8)


class Gap(Strict):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,60}$")
    description: str = Field(max_length=2000)
    kind: Literal["corpus_coverage_hole", "hypothesis", "candidate_gap", "unresolved"]
    significance: str = Field(max_length=2000)
    citations: list[Citation] = Field(default_factory=list, max_length=8)
    concerns: str = Field(max_length=2000)


class Review(Strict):
    gap_id: str
    disposition: Literal["survived", "contradicted", "insufficient"]
    rationale: str = Field(max_length=2000)
    counterevidence: list[Citation] = Field(default_factory=list, max_length=8)
    unresolved: str = Field(max_length=2000)


class SupportReview(Strict):
    claim_index: int = Field(ge=0)
    judgment: Literal["supported", "insufficient", "contradicted"]
    reason: str = Field(max_length=1500)


class Experiment(Strict):
    gap_id: str
    hypothesis: str = Field(max_length=2000)
    baselines: str = Field(max_length=2000)
    variables: str = Field(max_length=2000)
    datasets: str = Field(max_length=2000)
    metrics: str = Field(max_length=2000)
    refutation: str = Field(max_length=2000)
    resources: str = Field(max_length=2000)
    feasibility: str = Field(max_length=2000)


class RoleOutput(Strict):
    summary: str = Field(max_length=3500)
    queries: list[str] = Field(default_factory=list, max_length=3)
    coverage: list[str] = Field(default_factory=list, max_length=50)
    claims: list[Claim] = Field(default_factory=list, max_length=20)
    matrix: list[MatrixRow] = Field(default_factory=list, max_length=50)
    gaps: list[Gap] = Field(default_factory=list, max_length=8)
    reviews: list[Review] = Field(default_factory=list, max_length=8)
    support_reviews: list[SupportReview] = Field(default_factory=list, max_length=20)
    experiments: list[Experiment] = Field(default_factory=list, max_length=8)


class ResumeInput(Strict):
    acknowledge_duplicate_call: bool = False
    budget: Budget | None = None
