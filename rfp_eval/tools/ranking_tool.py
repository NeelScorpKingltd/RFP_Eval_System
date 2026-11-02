"""Single deterministic scoring, benchmarking, and ranking path."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import pairwise

from rfp_eval.domain.models import (
    Criterion,
    RankedSupplier,
    RankingResult,
    RankInput,
    ScorecardRow,
)
from rfp_eval.domain.rounding import round_half_up


def normalized_weights(criteria: Sequence[Criterion]) -> dict[int, float]:
    """Return active percentage weights divided by their sum, W."""
    active = sorted((c for c in criteria if c.is_active), key=lambda c: c.criterion_id)
    total = sum(c.weight for c in active)
    if not active or total <= 0:
        raise ValueError("Active criteria must have positive total weight")
    return {c.criterion_id: c.weight / total for c in active}


def absolute_weighted_score(scores: Mapping[int, float], criteria: Sequence[Criterion]) -> float:
    """Return Σ_c (s_c / m_c) * w_c on the 0-100 scale."""
    return sum(
        (scores.get(c.criterion_id, 0.0) / c.max_score) * c.weight for c in criteria if c.is_active
    )


def compute_benchmarks(
    all_scores: Sequence[Mapping[int, float]], criteria: Sequence[Criterion]
) -> dict[int, float]:
    """Return benchmark(c) = max over suppliers of s_c."""
    return {
        c.criterion_id: max((scores.get(c.criterion_id, 0.0) for scores in all_scores), default=0.0)
        for c in sorted(criteria, key=lambda item: item.criterion_id)
        if c.is_active
    }


def criterion_gap(score: float, benchmark: float) -> float:
    """Return gap(s, c) = s_c - benchmark(c)."""
    return score - benchmark


def relative_performance_pct(score: float, benchmark: float) -> float:
    """Return (score / benchmark) * 100, with the frozen zero-benchmark rule."""
    if benchmark > 0:
        return score / benchmark * 100
    return 100.0 if score == 0 else 0.0


def peer_performance_index(rel_pcts: Mapping[int, float], criteria: Sequence[Criterion]) -> float:
    """Return PPI(s) = Σ_c relative_pct(s,c) * (w_c / W)."""
    weights = normalized_weights(criteria)
    return sum(rel_pcts[ident] * weights[ident] for ident in sorted(weights))


def _scorecard(
    entry: RankInput, active: Sequence[Criterion], benchmarks: Mapping[int, float]
) -> tuple[list[ScorecardRow], dict[int, float], dict[int, float]]:
    by_id = {row.criterion_id: row for row in entry.evaluation.criteria}
    rows: list[ScorecardRow] = []
    scores: dict[int, float] = {}
    relatives: dict[int, float] = {}
    for criterion in active:
        source = by_id.get(criterion.criterion_id)
        score = source.score if source else 0.0
        benchmark = benchmarks[criterion.criterion_id]
        relative = relative_performance_pct(score, benchmark)
        scores[criterion.criterion_id] = score
        relatives[criterion.criterion_id] = relative
        rows.append(
            ScorecardRow(
                criterion_id=criterion.criterion_id,
                name=criterion.name,
                weight=criterion.weight,
                score=score,
                max_score=criterion.max_score,
                benchmark=benchmark,
                gap=round_half_up(criterion_gap(score, benchmark)),
                relative_pct=round_half_up(relative),
                weighted_contribution=round_half_up(score / criterion.max_score * criterion.weight),
                justification=source.justification if source else "",
                evidence=source.evidence if source else "",
            )
        )
    return rows, scores, relatives


def rank_suppliers(entries: Sequence[RankInput], criteria: Sequence[Criterion]) -> RankingResult:
    """Compute benchmark, absolute score, PPI, and four-tier sequential ranks."""
    active = sorted((c for c in criteria if c.is_active), key=lambda c: c.criterion_id)
    normalized_weights(active)
    if len({e.supplier_name.casefold() for e in entries}) != len(entries):
        raise ValueError("Supplier names must be unique")
    score_maps = [
        {row.criterion_id: row.score for row in entry.evaluation.criteria} for entry in entries
    ]
    benchmarks = compute_benchmarks(score_maps, active)
    scored: list[RankedSupplier] = []
    for entry in entries:
        scorecard, scores, relatives = _scorecard(entry, active, benchmarks)
        scored.append(
            RankedSupplier(
                final_rank=0,
                supplier_name=entry.supplier_name,
                submission_date=entry.submission_date,
                experience_rating=entry.experience_rating,
                absolute_score=round_half_up(absolute_weighted_score(scores, active)),
                ppi=round_half_up(peer_performance_index(relatives, active)),
                scorecard=scorecard,
            )
        )
    scored.sort(
        key=lambda s: (-s.ppi, s.submission_date, -s.experience_rating, s.supplier_name.lower())
    )
    for rank, supplier in enumerate(scored, 1):
        supplier.final_rank = rank
    return RankingResult(
        benchmarks=benchmarks,
        suppliers=scored,
        tie_break_explanations=build_tie_break_explanations(scored),
    )


def build_tie_break_explanations(ranked: Sequence[RankedSupplier]) -> list[str]:
    """Explain each adjacent pair using architecture.md §10.4 byte-exact templates."""
    explanations: list[str] = []
    for a, b in pairwise(ranked):
        k, na, nb = a.final_rank, a.supplier_name, b.supplier_name
        pa, pb = f"{a.ppi:.2f}", f"{b.ppi:.2f}"
        da, db = a.submission_date.isoformat(), b.submission_date.isoformat()
        ra, rb = f"{a.experience_rating:.1f}", f"{b.experience_rating:.1f}"
        if a.ppi != b.ppi:
            line = (
                f"Rank {k} ({na}) ranked above Rank {k + 1} ({nb}) via Tier 1 rule: "
                f"Higher PPI ({pa} vs {pb})."
            )
        elif a.submission_date != b.submission_date:
            line = (
                f"Rank {k} ({na}) and Rank {k + 1} ({nb}) tied on PPI ({pa}). "
                f"Tie resolved via Tier 2 rule: Earlier Submission Date ({da} vs {db})."
            )
        elif a.experience_rating != b.experience_rating:
            line = (
                f"Rank {k} ({na}) and Rank {k + 1} ({nb}) tied on PPI ({pa}) and "
                f"Submission Date ({da}). Tie resolved via Tier 3 rule: Higher "
                f"Historical Experience Rating ({ra} vs {rb})."
            )
        else:
            line = (
                f"Rank {k} ({na}) and Rank {k + 1} ({nb}) tied on PPI ({pa}), "
                f"Submission Date ({da}) and Experience Rating ({ra}). Tie resolved "
                f"via Tier 4 rule: Supplier Name alphabetical order "
                f"({na.lower()} vs {nb.lower()})."
            )
        explanations.append(line)
    return explanations
