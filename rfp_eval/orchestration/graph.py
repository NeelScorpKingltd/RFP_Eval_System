"""LangGraph wiring for the sequential evaluation pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from langgraph.graph import END, START, StateGraph

from rfp_eval.orchestration.nodes import (
    benchmark_node,
    cache_check_node,
    evaluate_node,
    persist_failure_node,
    persist_node,
    rank_node,
    sanitize_node,
    score_node,
    validate_node,
)
from rfp_eval.orchestration.progress import ProgressReporter
from rfp_eval.orchestration.state import RunState

if TYPE_CHECKING:
    from rfp_eval.orchestration.runner import Deps


def route_after_sanitize(state: RunState) -> str:
    """Abort if preflight left fewer than two usable proposals."""
    return "abort" if state.get("fatal_error") else "continue"


def build_graph(deps: Deps, reporter: ProgressReporter) -> Any:
    """Compile the eight-step graph with a failure persistence branch."""
    graph = StateGraph(RunState)
    nodes = (
        ("sanitize", sanitize_node(reporter)),
        ("cache_check", cache_check_node(deps, reporter)),
        ("evaluate", evaluate_node(deps, reporter)),
        ("validate", validate_node(deps, reporter)),
        ("score", score_node(reporter)),
        ("benchmark", benchmark_node(reporter)),
        ("rank", rank_node(reporter)),
        ("persist", persist_node(deps, reporter)),
        ("persist_failure", persist_failure_node(deps, reporter)),
    )
    for name, node in nodes:
        graph.add_node(name, cast(Any, node))
    graph.add_edge(START, "sanitize")
    graph.add_conditional_edges(
        "sanitize",
        route_after_sanitize,
        {"continue": "cache_check", "abort": "persist_failure"},
    )
    graph.add_edge("cache_check", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        route_after_sanitize,
        {"continue": "validate", "abort": "persist_failure"},
    )
    graph.add_edge("validate", "score")
    graph.add_edge("score", "benchmark")
    graph.add_edge("benchmark", "rank")
    graph.add_edge("rank", "persist")
    graph.add_edge("persist", END)
    graph.add_edge("persist_failure", END)
    return graph.compile()
