"""Deterministic Markdown download for a validated BAFO playbook."""

from __future__ import annotations

from rfp_eval.domain.models import WinnerNegotiationPlaybook


def _line(value: str) -> str:
    return value.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")


def _cell(value: str) -> str:
    return _line(value).replace("|", r"\|")


def render_negotiation_briefing(playbook: WinnerNegotiationPlaybook) -> str:
    """Render a stable Markdown briefing with priority from matrix row order."""
    lines = [
        "# BAFO Negotiation Briefing",
        "",
        "## Negotiation stance",
        "",
        _line(playbook.stance),
        "",
        "## Leverage areas",
        "",
        *[f"- {_line(item)}" for item in playbook.leverage_areas],
        "",
        "## Negotiation matrix",
        "",
        "| Priority | Category | Proposal Vulnerability | Target Concession | "
        "Scripted Meeting Question |",
        "|---:|---|---|---|---|",
    ]
    for index, item in enumerate(playbook.negotiation_matrix, 1):
        fields = (
            str(index),
            item.category,
            item.proposal_vulnerability,
            item.target_concession,
            item.scripted_meeting_question,
        )
        lines.append("| " + " | ".join(_cell(value) for value in fields) + " |")
    lines.extend(["", "## Walkaway risks", ""])
    lines.extend(f"- {_line(item)}" for item in playbook.walkaway_risks)
    lines.append("")
    return "\n".join(lines)
