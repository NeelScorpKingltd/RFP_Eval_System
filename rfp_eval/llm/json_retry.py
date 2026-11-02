"""Two-attempt extraction and repair of structured LLM output."""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from rfp_eval.domain.models import RawEvaluation
from rfp_eval.llm.base import LLMClient

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def parse_llm_json(raw: str) -> dict[str, object]:
    """Extract the first complete JSON object, allowing fences and surrounding prose."""
    cleaned = _FENCE.sub("", raw.strip())
    decoder = json.JSONDecoder()
    for index, character in enumerate(cleaned):
        if character != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError("No valid JSON object found")


def call_with_json_retry(
    client: LLMClient,
    system: str,
    user: str,
    *,
    validate: Callable[[dict[str, object]], None],
    max_attempts: int = 2,
) -> RawEvaluation:
    """Ask for corrected JSON once after a parse or schema failure."""
    errors: list[str] = []
    prompt = user
    for attempt in range(1, max_attempts + 1):
        reply = client.complete(system, prompt)
        try:
            payload = parse_llm_json(reply.text)
            validate(payload)
            return RawEvaluation(payload=payload, attempts=attempt, errors=errors)
        except (ValueError, TypeError, KeyError) as exc:
            error = str(exc)[:200]
            errors.append(error)
            prompt = (
                user + f"\nYour previous output failed validation: {error}. "
                "Return corrected JSON only."
            )
    return RawEvaluation(payload=None, attempts=max_attempts, errors=errors)
