"""Run lifecycle, gate enforcement, and dependency injection."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import cast

from rfp_eval.db.repositories import CriteriaRepo, RunRepo, SupplierResultRepo
from rfp_eval.domain.enums import RunStatus
from rfp_eval.domain.errors import ConfigError, GateViolation, LLMAuthError
from rfp_eval.domain.models import CacheStats, Criterion, RunMeta, RunResult
from rfp_eval.llm.base import LLMClient
from rfp_eval.llm.prompts import EVAL_PROMPT_VERSION
from rfp_eval.orchestration.graph import build_graph
from rfp_eval.orchestration.progress import NullReporter, ProgressReporter
from rfp_eval.orchestration.state import RunRequest, RunState
from rfp_eval.tools.cache import MemoryCache
from rfp_eval.tools.weight_gate import check_weight_gate

_LOG = logging.getLogger(__name__)


@dataclass
class Deps:
    criteria_repo: CriteriaRepo
    run_repo: RunRepo
    result_repo: SupplierResultRepo
    llm: LLMClient
    memory_cache: MemoryCache
    clock: Callable[[], datetime]


def _check_request(request: RunRequest, deps: Deps) -> list[Criterion]:
    criteria = deps.criteria_repo.list_all()
    gate = check_weight_gate(criteria)
    if not gate.valid:
        raise GateViolation(gate.message)
    if len(request.suppliers) < 2:
        raise GateViolation("At least two suppliers are required.")
    if any(not isinstance(supplier.supplier_name, str) for supplier in request.suppliers):
        raise GateViolation("Every supplier needs a name.")
    names = [supplier.supplier_name.strip() for supplier in request.suppliers]
    if any(not name for name in names):
        raise GateViolation("Every supplier needs a name.")
    if len({name.casefold() for name in names}) != len(names):
        raise GateViolation("Supplier names must be unique.")
    if any(not isinstance(supplier.submission_date, date) for supplier in request.suppliers):
        raise GateViolation("Every supplier needs a valid submission date.")
    if any(
        not isinstance(supplier.experience_rating, (int, float))
        or not math.isfinite(supplier.experience_rating)
        or not 0 <= supplier.experience_rating <= 5
        for supplier in request.suppliers
    ):
        raise GateViolation("Experience ratings must be between 0 and 5.")
    if any(not supplier.pdf_name or not supplier.pdf_bytes for supplier in request.suppliers):
        raise GateViolation("Every supplier needs a PDF.")
    return criteria


def run_evaluation(
    request: RunRequest, deps: Deps, reporter: ProgressReporter | None = None
) -> RunResult:
    """Gate inputs, run the graph, and return a persisted result or safe failure."""
    criteria = _check_request(request, deps)
    current = deps.clock().astimezone(UTC)
    run_id = deps.run_repo.create(current)
    progress = reporter or NullReporter()
    state: RunState = {
        "run_id": run_id,
        "criteria": criteria,
        "suppliers": request.suppliers,
        "fault_mode": request.fault_mode,
        "warnings": [],
        "status": RunStatus.IN_PROGRESS,
        "fatal_error": None,
    }
    try:
        final = cast(RunState, build_graph(deps, progress).invoke(state))
    except (LLMAuthError, ConfigError):
        deps.run_repo.set_status(run_id, RunStatus.FAILED)
        _LOG.error("Run %s failed authentication", run_id)
        raise
    except Exception as exc:
        deps.run_repo.set_status(run_id, RunStatus.FAILED)
        _LOG.error("Run %s failed with %s", run_id, type(exc).__name__)
        raise RuntimeError(
            f"Evaluation failed for {run_id}; check the run configuration."
        ) from None
    return RunResult(
        rfp_run_id=run_id,
        created_at=current,
        status=final["status"],
        active_criteria=[item for item in criteria if item.is_active],
        ranking=final.get("ranking"),
        evaluations=final.get("evaluations", {}),
        validation_warnings=final.get("warnings", []),
        security_findings={name: doc.findings for name, doc in final["documents"].items()},
        cache_stats=CacheStats.model_validate(final.get("cache_stats", {})),
        meta=RunMeta(
            provider=deps.llm.provider.value,
            model=deps.llm.model,
            fault_mode=request.fault_mode,
            prompt_version=EVAL_PROMPT_VERSION,
        ),
    )
