"""Dependencies shared by the five Streamlit screens."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from rfp_eval.db.repositories import CriteriaRepo, RunRepo, SupplierResultRepo
from rfp_eval.llm.base import LLMSettings


class ScreenContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    criteria_repo: CriteriaRepo
    run_repo: RunRepo
    result_repo: SupplierResultRepo
    llm_settings: LLMSettings | None = None
    fault_mode: bool = False
