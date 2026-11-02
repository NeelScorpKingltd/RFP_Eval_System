"""FR-LLM-04 parser repair and two-attempt fallback."""

from __future__ import annotations

from rfp_eval.llm.fake import FakeLLMClient
from rfp_eval.llm.json_retry import call_with_json_retry, parse_llm_json


def require_criteria(payload: dict[str, object]) -> None:
    if not isinstance(payload.get("criteria"), list):
        raise ValueError("criteria must be a list")


def test_fr_llm_04_fenced_and_surrounded_json() -> None:
    assert parse_llm_json('```json\n{"criteria": []}\n```') == {"criteria": []}
    assert parse_llm_json('Here is JSON: {"criteria": []} Thanks.') == {"criteria": []}


def test_fr_llm_04_trailing_comma_retries_with_feedback() -> None:
    fake = FakeLLMClient(['{"criteria": [],}', '{"criteria": []}'])
    raw = call_with_json_retry(fake, "system", "user", validate=require_criteria)
    assert raw.attempts == 2
    assert raw.payload == {"criteria": []}
    assert "failed validation" in fake.calls[1][1]


def test_fr_llm_04_two_bad_replies_fall_back() -> None:
    fake = FakeLLMClient(["no json", '{"criteria": 42}'])
    raw = call_with_json_retry(fake, "system", "user", validate=require_criteria)
    assert raw.payload is None
    assert raw.attempts == 2
    assert len(raw.errors) == 2
