"""Sequential LangGraph nodes for one evaluation batch."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from rfp_eval.agents.evaluation_agent import EvaluationAgent
from rfp_eval.domain.enums import PipelineStep, RunStatus
from rfp_eval.domain.errors import DocumentRejected, LLMOutputError, LLMTransportError
from rfp_eval.domain.models import RankInput, RawEvaluation
from rfp_eval.llm.fault_injection import FaultInjector
from rfp_eval.orchestration.cache_reader import rebuild_cached_evaluation, with_current_name
from rfp_eval.orchestration.persistence import build_stored_rows
from rfp_eval.orchestration.progress import ProgressReporter
from rfp_eval.orchestration.state import RunState
from rfp_eval.tools.cache import compute_cache_hash
from rfp_eval.tools.document_tool import sanitize_pdf
from rfp_eval.tools.ranking_tool import (
    absolute_weighted_score,
    compute_benchmarks,
    rank_suppliers,
)
from rfp_eval.tools.validation_tool import validate_evaluation

if TYPE_CHECKING:
    from rfp_eval.orchestration.runner import Deps

Node = Callable[[RunState], RunState]
_LOG = logging.getLogger(__name__)


def sanitize_node(reporter: ProgressReporter) -> Node:
    """Reject invalid PDFs individually and abort when fewer than two survive."""

    def run(state: RunState) -> RunState:
        reporter.step_started(PipelineStep.SANITIZE)
        documents = {}
        rejections = {}
        warnings: list[str] = []
        for index, supplier in enumerate(state["suppliers"], 1):
            try:
                document = sanitize_pdf(
                    supplier.supplier_name,
                    supplier.pdf_name,
                    supplier.pdf_bytes,
                )
                documents[supplier.supplier_name] = document
                if document.findings:
                    _LOG.info(
                        "Run %s supplier %s: %d security findings",
                        state["run_id"],
                        supplier.supplier_name,
                        len(document.findings),
                    )
            except DocumentRejected as exc:
                rejections[supplier.supplier_name] = str(exc)
                warnings.append(str(exc))
                reporter.warning(str(exc))
            reporter.step_progress(PipelineStep.SANITIZE, index, len(state["suppliers"]))
        reporter.step_finished(PipelineStep.SANITIZE)
        result: RunState = {"documents": documents, "rejections": rejections, "warnings": warnings}
        if len(documents) < 2:
            result["fatal_error"] = "At least two valid supplier PDFs are required."
        return result

    return run


def cache_check_node(deps: Deps, reporter: ProgressReporter) -> Node:
    """Look up memory and completed SQLite rows unless demo fault mode is enabled."""

    def run(state: RunState) -> RunState:
        reporter.step_started(PipelineStep.CACHE)
        hashes = {}
        hits = {}
        misses = 0
        for index, supplier in enumerate(state["suppliers"], 1):
            name = supplier.supplier_name
            if name not in state["documents"]:
                continue
            key = compute_cache_hash(supplier.pdf_bytes, state["criteria"])
            hashes[name] = key
            evaluation = deps.memory_cache.get(key, fault_mode=state["fault_mode"])
            if evaluation is None and not state["fault_mode"]:
                stored = deps.result_repo.find_by_cache_hash(key)
                if stored is not None:
                    evaluation = rebuild_cached_evaluation(stored, name)
                    deps.memory_cache.put(key, evaluation)
            if evaluation is None:
                misses += 1
            else:
                hits[name] = with_current_name(evaluation, name)
            reporter.step_progress(PipelineStep.CACHE, index, len(state["suppliers"]))
        reporter.step_finished(PipelineStep.CACHE)
        return {
            "cache_hashes": hashes,
            "cache_hits": hits,
            "cache_stats": {"hits": len(hits), "misses": misses, "llm_calls": 0, "fallbacks": 0},
        }

    return run


def evaluate_node(deps: Deps, reporter: ProgressReporter) -> Node:
    """Call the selected LLM only for cache misses, with supplier-level fallback."""

    def run(state: RunState) -> RunState:
        reporter.step_started(PipelineStep.EVALUATE)
        target = next(iter(state["documents"]))
        fault = FaultInjector(target) if state["fault_mode"] else None
        agent = EvaluationAgent(deps.llm, fault)
        raw = {}
        warnings: list[str] = []
        calls = 0
        transport_failures = 0
        for index, supplier in enumerate(state["suppliers"], 1):
            name = supplier.supplier_name
            if name not in state["documents"] or name in state["cache_hits"]:
                continue
            try:
                raw[name] = agent.evaluate(state["documents"][name], state["criteria"])
                calls += raw[name].attempts
            except (LLMTransportError, LLMOutputError) as error:
                raw[name] = RawEvaluation(payload=None, attempts=1)
                calls += 1
                transport_failures += 1
                message = f"{name}: LLM request failed; all criteria set to 0."
                warnings.append(message)
                reporter.warning(message)
                warnings.append(f"{name}: {error}")
            reporter.step_progress(PipelineStep.EVALUATE, index, len(state["suppliers"]))
        reporter.step_finished(PipelineStep.EVALUATE)
        stats = dict(state["cache_stats"])
        stats["llm_calls"] = calls
        result: RunState = {
            "raw": raw,
            "warnings": warnings,
            "cache_stats": stats,
            "transport_failures": transport_failures,
        }
        if transport_failures == len(state["documents"]) and not state["cache_hits"]:
            result["fatal_error"] = "All supplier LLM requests failed; no ranking was produced."
        return result

    return run


def validate_node(deps: Deps, reporter: ProgressReporter) -> Node:
    """Normalize LLM payloads and cache valid output outside fault mode."""

    def run(state: RunState) -> RunState:
        reporter.step_started(PipelineStep.VALIDATE)
        evaluations = dict(state["cache_hits"])
        warnings: list[str] = []
        fallbacks = 0
        for index, supplier in enumerate(state["suppliers"], 1):
            name = supplier.supplier_name
            if name not in state["documents"]:
                continue
            if name not in evaluations:
                raw = state["raw"][name]
                evaluations[name] = validate_evaluation(raw, name, state["criteria"])
                if raw.payload is None:
                    fallbacks += 1
                if raw.payload is not None:
                    deps.memory_cache.put(
                        state["cache_hashes"][name],
                        evaluations[name],
                        fault_mode=state["fault_mode"],
                    )
            for warning in evaluations[name].warnings:
                warnings.append(warning)
                reporter.warning(warning)
            reporter.step_progress(PipelineStep.VALIDATE, index, len(state["suppliers"]))
        reporter.step_finished(PipelineStep.VALIDATE)
        stats = dict(state["cache_stats"])
        stats["fallbacks"] = fallbacks
        return {"evaluations": evaluations, "warnings": warnings, "cache_stats": stats}

    return run


def score_node(reporter: ProgressReporter) -> Node:
    """Compute absolute scores through ranking_tool only."""

    def run(state: RunState) -> RunState:
        reporter.step_started(PipelineStep.SCORE)
        scores = {
            name: absolute_weighted_score(
                {item.criterion_id: item.score for item in evaluation.criteria}, state["criteria"]
            )
            for name, evaluation in state["evaluations"].items()
        }
        reporter.step_finished(PipelineStep.SCORE)
        return {"absolute_scores": scores}

    return run


def benchmark_node(reporter: ProgressReporter) -> Node:
    """Compute peer maxima through ranking_tool only."""

    def run(state: RunState) -> RunState:
        reporter.step_started(PipelineStep.BENCHMARK)
        all_scores = [
            {item.criterion_id: item.score for item in evaluation.criteria}
            for evaluation in state["evaluations"].values()
        ]
        result = compute_benchmarks(all_scores, state["criteria"])
        reporter.step_finished(PipelineStep.BENCHMARK)
        return {"benchmarks": result}

    return run


def rank_node(reporter: ProgressReporter) -> Node:
    """Build the one deterministic ranking and explanation set."""

    def run(state: RunState) -> RunState:
        reporter.step_started(PipelineStep.RANK)
        entries = [
            RankInput(
                supplier_name=item.supplier_name,
                submission_date=item.submission_date,
                experience_rating=item.experience_rating,
                evaluation=state["evaluations"][item.supplier_name],
            )
            for item in state["suppliers"]
            if item.supplier_name in state["documents"]
        ]
        ranking = rank_suppliers(entries, state["criteria"])
        reporter.step_finished(PipelineStep.RANK)
        return {"ranking": ranking}

    return run


def persist_node(deps: Deps, reporter: ProgressReporter) -> Node:
    """Commit all supplier rows and the completed status atomically."""

    def run(state: RunState) -> RunState:
        reporter.step_started(PipelineStep.PERSIST)
        deps.result_repo.save_completed(state["run_id"], build_stored_rows(state, deps))
        reporter.step_finished(PipelineStep.PERSIST)
        return {"status": RunStatus.COMPLETED}

    return run


def persist_failure_node(deps: Deps, reporter: ProgressReporter) -> Node:
    """Record a run that has too few valid documents."""

    def run(state: RunState) -> RunState:
        reporter.step_started(PipelineStep.PERSIST)
        deps.run_repo.set_status(state["run_id"], RunStatus.FAILED)
        reporter.warning(state["fatal_error"] or "Run failed.")
        reporter.step_finished(PipelineStep.PERSIST)
        return {"status": RunStatus.FAILED, "warnings": [state["fatal_error"] or "Run failed."]}

    return run
