"""Main-thread Streamlit progress adapter for the LangGraph reporter protocol."""

from __future__ import annotations

import streamlit as st

from rfp_eval.domain.enums import PipelineStep

_WEIGHTS = {
    PipelineStep.SANITIZE: 0.10,
    PipelineStep.CACHE: 0.05,
    PipelineStep.EVALUATE: 0.55,
    PipelineStep.VALIDATE: 0.05,
    PipelineStep.SCORE: 0.05,
    PipelineStep.BENCHMARK: 0.05,
    PipelineStep.RANK: 0.05,
    PipelineStep.PERSIST: 0.10,
}


class StreamlitProgressReporter:
    """Update one status container and progress bar on the calling script thread."""

    def __init__(self) -> None:
        self.status = st.status("Preparing evaluation", expanded=True)
        self.bar = st.progress(0)
        self.completed: set[PipelineStep] = set()

    def step_started(self, step: PipelineStep, detail: str = "") -> None:
        """Show the current graph step."""
        self.status.write(f"{step.value.replace('_', ' ').title()} started")

    def step_progress(self, step: PipelineStep, done: int, total: int, detail: str = "") -> None:
        """Advance the weighted bar during sequential supplier work."""
        base = sum(_WEIGHTS[item] for item in self.completed)
        fraction = done / total if total else 0
        self.bar.progress(min(1.0, base + _WEIGHTS[step] * fraction))

    def step_finished(self, step: PipelineStep, detail: str = "") -> None:
        """Mark a graph step complete."""
        self.completed.add(step)
        self.bar.progress(min(1.0, sum(_WEIGHTS[item] for item in self.completed)))
        self.status.write(f"{step.value.replace('_', ' ').title()} complete")
        if step == PipelineStep.PERSIST:
            self.status.update(label="Evaluation finished", state="complete")

    def warning(self, message: str) -> None:
        """Show a supplier warning as plain text inside the status container."""
        self.status.write(message)

    def failed(self) -> None:
        """Close the status container after a run-level exception."""
        self.status.update(label="Evaluation failed", state="error")
