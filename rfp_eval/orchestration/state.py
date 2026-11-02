"""Typed request and LangGraph state for one evaluation run."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from pydantic import BaseModel

from rfp_eval.domain.enums import RunStatus
from rfp_eval.domain.models import (
    Criterion,
    RankingResult,
    RawEvaluation,
    SanitizedDocument,
    SupplierInput,
    ValidatedEvaluation,
)


class RunRequest(BaseModel):
    suppliers: list[SupplierInput]
    fault_mode: bool = False


class RunState(TypedDict, total=False):
    run_id: str
    criteria: list[Criterion]
    suppliers: list[SupplierInput]
    fault_mode: bool
    documents: dict[str, SanitizedDocument]
    rejections: dict[str, str]
    cache_hashes: dict[str, str]
    cache_hits: dict[str, ValidatedEvaluation]
    raw: dict[str, RawEvaluation]
    evaluations: dict[str, ValidatedEvaluation]
    absolute_scores: dict[str, float]
    benchmarks: dict[int, float]
    ranking: RankingResult
    warnings: Annotated[list[str], operator.add]
    status: RunStatus
    fatal_error: str | None
    cache_stats: dict[str, int]
    transport_failures: int
