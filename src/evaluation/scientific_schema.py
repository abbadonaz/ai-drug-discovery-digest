"""Versioned annotations; review metadata is a human assertion, not authentication."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Category = Literal["finding", "method", "result", "comparison", "limitation"]
Support = Literal["supported", "contradicted", "insufficient_evidence", "not_assessed"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Passage(StrictModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    section: str
    page: int | None = Field(default=None, ge=1)


class Annotation(StrictModel):
    id: str = Field(min_length=1)
    category: Category
    statement: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    # Full sentences only: no substring/keyword entailment claims.
    accepted_statements: list[str] = Field(default_factory=list)


class Quantity(StrictModel):
    annotation_id: str
    value: str = Field(min_length=1)
    unit: str = Field(min_length=1)  # use dimensionless when appropriate
    metric: str = Field(min_length=1)
    dataset: str = Field(min_length=1)
    direction: str = Field(min_length=1)
    conditions: str = Field(min_length=1)
    baseline: str = Field(min_length=1)


class NegativeControl(StrictModel):
    id: str
    statement: str = Field(min_length=1)
    error_type: Literal["value", "unit", "metric", "dataset", "direction", "conditions",
                        "validation", "experimental_confirmation", "significance",
                        "superiority", "unsupported_result", "qualification"]
    support: Literal["contradicted", "insufficient_evidence"]
    evidence_ids: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    annotation_id: str | None = None


class Review(StrictModel):
    status: Literal["synthetic", "unreviewed", "verified"]
    annotator: str = Field(min_length=1)
    reviewer: str | None = None
    reviewed_at: str | None = None
    notes: str = Field(min_length=1)


class Case(StrictModel):
    id: str = Field(min_length=1)
    kind: Literal["synthetic", "real"]
    title: str = Field(min_length=1)
    identifier: str | None = None
    url: str | None = None
    domain: Literal["qsar_admet", "representations_gnn", "uncertainty", "active_learning",
                    "generative_design", "structure_based", "foundation_models"]
    source_ref: str = Field(min_length=1)
    source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    evidence_scope: Literal["abstract_only", "full_text", "unknown"]
    passages: list[Passage] = Field(default_factory=list)
    annotations: list[Annotation] = Field(default_factory=list)
    quantities: list[Quantity] = Field(default_factory=list)
    must_not_infer: list[NegativeControl] = Field(default_factory=list)
    reference_summary: str | None = None
    review: Review

    @model_validator(mode="after")
    def consistent_annotations(self):
        if (self.kind == "synthetic") != (self.review.status == "synthetic"):
            raise ValueError("Synthetic cases must be labeled synthetic, never human-verified")
        if self.review.status == "verified" and not all((
            self.review.reviewer, self.review.reviewed_at, self.source_sha256,
            self.passages, self.annotations,
        )):
            raise ValueError("Verified real cases need reviewer/date, source hash, passages and annotations")
        for items in (self.passages, self.annotations, self.must_not_infer):
            if len({item.id for item in items}) != len(items):
                raise ValueError("Duplicate annotation/passage/control IDs")
        evidence_ids = {item.id for item in self.passages}
        annotation_ids = {item.id for item in self.annotations}
        for item in [*self.annotations, *self.must_not_infer]:
            if not set(item.evidence_ids) <= evidence_ids:
                raise ValueError("Unknown evidence reference")
        for item in self.quantities:
            if item.annotation_id not in annotation_ids:
                raise ValueError("Unknown quantitative annotation")
        for item in self.must_not_infer:
            if item.annotation_id and item.annotation_id not in annotation_ids:
                raise ValueError("Unknown negative-control annotation")
        return self

    @property
    def cohort(self):
        return "synthetic" if self.kind == "synthetic" else self.review.status


class Benchmark(StrictModel):
    schema_version: Literal["1.0"]
    benchmark_version: str = Field(min_length=1)
    cases: list[Case]

    @model_validator(mode="after")
    def unique_cases(self):
        if len({case.id for case in self.cases}) != len(self.cases):
            raise ValueError("Duplicate case IDs")
        return self


class ClaimJudgment(StrictModel):
    claim: str = Field(min_length=1)
    status: Support
    evidence_ids: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1)


class HumanAssessment(StrictModel):
    case_id: str
    benchmark_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    summary_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)
    claims: list[ClaimJudgment] = Field(default_factory=list)
    # Optional ordinal judgments; never auto-populated or pooled with automation.
    rubric: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def rubric_values(self):
        dimensions = {"accuracy", "methodology", "quantitative_information", "coverage",
                      "limitations", "drug_discovery_relevance"}
        if not self.rubric.keys() <= dimensions or any(value not in range(4) for value in self.rubric.values()):
            raise ValueError("Rubric scores must be 0..3 in documented dimensions")
        return self
