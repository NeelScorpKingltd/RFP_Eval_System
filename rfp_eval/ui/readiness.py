"""Shared readiness gate for criteria, suppliers, and model setup."""

from __future__ import annotations

from pydantic import BaseModel

from rfp_eval.domain.models import Criterion
from rfp_eval.tools.weight_gate import check_weight_gate
from rfp_eval.ui.state import SupplierDraft


class Readiness(BaseModel):
    blocking: list[str]
    warnings: list[str]

    @property
    def ready(self) -> bool:
        return not self.blocking


def assess_readiness(
    criteria: list[Criterion],
    drafts: list[SupplierDraft],
    llm_ready: bool,
) -> Readiness:
    """Return all gate failures before enabling Evaluate."""
    blocking: list[str] = []
    warnings: list[str] = []
    gate = check_weight_gate(criteria)
    if not gate.valid:
        blocking.append(gate.message)
    usable = [draft for draft in drafts if draft.document is not None]
    if len(usable) < 2:
        blocking.append("Add at least two valid supplier PDFs.")
    names = [draft.supplier_name.strip() for draft in usable]
    if any(not name for name in names):
        blocking.append("Every valid supplier needs a name.")
    if len({name.casefold() for name in names}) != len(names):
        blocking.append("Supplier names must be unique.")
    if any(draft.submission_date is None for draft in usable):
        blocking.append("Every valid supplier needs a submission date.")
    if any(
        draft.experience_rating is None or not 0 <= draft.experience_rating <= 5 for draft in usable
    ):
        blocking.append("Every valid supplier needs an experience rating from 0 to 5.")
    if not llm_ready:
        blocking.append(
            "Select an LLM provider and enter a key, or enable the configured demo model."
        )
    rejected = [draft for draft in drafts if draft.rejection]
    if rejected:
        warnings.append(f"{len(rejected)} PDF(s) were rejected and will be excluded.")
    return Readiness(blocking=blocking, warnings=warnings)
