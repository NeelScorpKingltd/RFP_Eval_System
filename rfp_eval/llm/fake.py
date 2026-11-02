"""Deterministic fake client for offline tests and demonstrations."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from rfp_eval.domain.enums import Provider
from rfp_eval.llm.base import LLMReply


class FakeLLMClient:
    provider = Provider.OPENAI
    model = "fake"

    def __init__(self, replies: Iterable[str | Exception]) -> None:
        self.replies = deque(replies)
        self.calls: list[tuple[str, str]] = []

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.0,
        json_mode: bool = True,
        max_tokens: int = 4096,
    ) -> LLMReply:
        """Return the next scripted reply and record the prompt."""
        self.calls.append((system, user))
        if not self.replies:
            raise AssertionError("No scripted fake LLM reply remains")
        reply = self.replies.popleft()
        if isinstance(reply, Exception):
            raise reply
        return LLMReply(text=reply)
