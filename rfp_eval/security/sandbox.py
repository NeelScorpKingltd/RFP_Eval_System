"""Mark PDF contents as passive audit data in LLM prompts."""

from __future__ import annotations

import re

OPEN_TAG = "<untrusted_proposal_content>"
CLOSE_TAG = "</untrusted_proposal_content>"
_TAGS = re.compile(r"<(/?untrusted_proposal_content)\s*>", re.IGNORECASE)


def wrap_untrusted(text: str) -> str:
    """Neutralise embedded boundary tags, then wrap the source text."""
    escaped = _TAGS.sub(lambda match: "&lt;" + match.group(1) + ">", text)
    return f"{OPEN_TAG}\n{escaped}\n{CLOSE_TAG}"
