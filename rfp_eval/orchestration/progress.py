"""Progress reporting boundary between the graph and Streamlit UI."""

from __future__ import annotations

from typing import Protocol

from rfp_eval.domain.enums import PipelineStep


class ProgressReporter(Protocol):
    def step_started(self, step: PipelineStep, detail: str = "") -> None: ...

    def step_progress(
        self, step: PipelineStep, done: int, total: int, detail: str = ""
    ) -> None: ...

    def step_finished(self, step: PipelineStep, detail: str = "") -> None: ...

    def warning(self, message: str) -> None: ...


class NullReporter:
    """No-op reporter for scripts and tests."""

    def step_started(self, step: PipelineStep, detail: str = "") -> None:
        """Ignore step start."""

    def step_progress(self, step: PipelineStep, done: int, total: int, detail: str = "") -> None:
        """Ignore step progress."""

    def step_finished(self, step: PipelineStep, detail: str = "") -> None:
        """Ignore step finish."""

    def warning(self, message: str) -> None:
        """Ignore warnings."""
