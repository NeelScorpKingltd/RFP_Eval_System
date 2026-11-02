"""Validated data passed between application layers."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from rfp_eval.domain.enums import RunStatus


class Criterion(BaseModel):
    criterion_id: int
    name: str
    description: str
    weight: float
    max_score: int = Field(ge=1)
    is_active: bool = True


class SupplierInput(BaseModel):
    supplier_name: str
    submission_date: date
    experience_rating: float = Field(ge=0, le=5)
    pdf_name: str
    pdf_bytes: bytes = Field(repr=False, exclude=True)


class InjectionFinding(BaseModel):
    kind: Literal["phrase", "hidden_text"]
    pattern: str
    snippet: str
    page: int | None = None


class SanitizedDocument(BaseModel):
    supplier_name: str
    text: str
    page_count: int
    size_bytes: int
    pdf_sha256: str
    findings: list[InjectionFinding]


class CriterionResult(BaseModel):
    criterion_id: int
    score: float
    max_score: int
    justification: str
    evidence: str = ""


class ProcurementRisk(BaseModel):
    risk_category: str
    severity: Literal["High", "Medium", "Low"]
    issue: str
    verbatim_excerpt: str


class ValidatedEvaluation(BaseModel):
    supplier_name: str
    overall_summary: str
    criteria: list[CriterionResult]
    procurement_risks: list[ProcurementRisk]
    warnings: list[str]
    llm_attempts: int


class RawEvaluation(BaseModel):
    payload: dict[str, object] | None
    attempts: int
    errors: list[str] = Field(default_factory=list)


class RankInput(BaseModel):
    supplier_name: str
    submission_date: date
    experience_rating: float
    evaluation: ValidatedEvaluation


class ScorecardRow(BaseModel):
    criterion_id: int
    name: str
    weight: float
    score: float
    max_score: int
    benchmark: float
    gap: float
    relative_pct: float
    weighted_contribution: float
    justification: str
    evidence: str


class RankedSupplier(BaseModel):
    final_rank: int
    supplier_name: str
    submission_date: date
    experience_rating: float
    absolute_score: float
    ppi: float
    scorecard: list[ScorecardRow]


class RankingResult(BaseModel):
    benchmarks: dict[int, float]
    suppliers: list[RankedSupplier]
    tie_break_explanations: list[str]


class SensitivityResult(BaseModel):
    ranking: RankingResult
    normalized_weights: dict[int, float]
    rank_deltas: dict[str, int]


class NegotiationPoint(BaseModel):
    category: str
    proposal_vulnerability: str
    target_concession: str
    scripted_meeting_question: str


class WinnerNegotiationPlaybook(BaseModel):
    stance: str
    leverage_areas: list[str]
    walkaway_risks: list[str]
    negotiation_matrix: list[NegotiationPoint]


class CacheStats(BaseModel):
    hits: int = 0
    misses: int = 0
    llm_calls: int = 0
    fallbacks: int = 0


class RunMeta(BaseModel):
    provider: str
    model: str
    fault_mode: bool = False
    prompt_version: str = "eval-v1"


class RunResult(BaseModel):
    rfp_run_id: str
    created_at: datetime
    status: RunStatus
    active_criteria: list[Criterion]
    ranking: RankingResult | None
    evaluations: dict[str, ValidatedEvaluation]
    validation_warnings: list[str]
    security_findings: dict[str, list[InjectionFinding]]
    cache_stats: CacheStats
    meta: RunMeta


class StoredSupplierResult(BaseModel):
    """A supplier result row at the SQLite boundary."""

    rfp_run_id: str
    supplier_name: str
    submission_date: date
    experience_rating: float
    absolute_score: float
    ppi: float
    final_rank: int
    result_json: str
    negotiation_playbook_json: str | None = None
    cache_hash: str | None = None


class StoredRun(BaseModel):
    rfp_run_id: str
    created_at: datetime
    status: RunStatus
