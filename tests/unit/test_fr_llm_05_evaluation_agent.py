"""FR-LLM-05 and FR-VAL-04 isolated prompt and fault demonstration."""

from __future__ import annotations

from rfp_eval.agents.evaluation_agent import EvaluationAgent
from rfp_eval.domain.models import Criterion, SanitizedDocument
from rfp_eval.llm.fake import FakeLLMClient
from rfp_eval.llm.fault_injection import FaultInjector
from rfp_eval.tools.validation_tool import validate_evaluation


def test_fr_val_04_fault_is_validated_and_prompt_has_no_weights() -> None:
    client = FakeLLMClient(
        [
            '{"supplier_name":"Apex","overall_summary":"Fine","criteria":'
            '[{"criterion_id":1,"score":8},{"criterion_id":2,"score":7}]}'
        ]
    )
    agent = EvaluationAgent(client, FaultInjector("Apex"))
    criteria = [
        Criterion(
            criterion_id=1, name="Technical", description="Architecture", weight=80, max_score=10
        ),
        Criterion(criterion_id=2, name="Support", description="Service", weight=20, max_score=10),
    ]
    document = SanitizedDocument(
        supplier_name="Apex",
        text="Proposal evidence " * 12,
        page_count=1,
        size_bytes=200,
        pdf_sha256="hash",
        findings=[],
    )
    output = validate_evaluation(agent.evaluate(document, criteria), "Apex", criteria)
    assert [row.score for row in output.criteria] == [10, 0]
    assert len(output.warnings) == 2
    system, user = client.calls[0]
    assert "weight=80" not in system and "weight=20" not in system
    assert "80" not in system and "20" not in system
    assert "<untrusted_proposal_content>" in user
    assert "Reminder:" in user
    assert "two concise, evidence-grounded sentences" in system
