"""Phase 3B deterministic scoring rules.

The functions in this module intentionally operate only on the canonical
financial and scoring schemas.  They do not fetch data or ask an LLM to make
numeric decisions.  A metric with no value, a non-finite value, or a value
outside its rule's domain is omitted and its remaining weights are scaled to
sum to one.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from math import isfinite
from typing import Final, Literal, cast

from app.schemas.financial import FinancialMetrics, MetricValue
from app.schemas.scoring import ScoreBreakdown, ScoreComponent

METHODOLOGY_VERSION: Final[str] = "phase3b-1.0"


@dataclass(frozen=True, slots=True)
class _MetricRule:
    name: str
    weight: float
    minimum: float
    maximum: float
    higher_is_better: bool = True
    normalizer: Callable[[float], float] | None = None


def _linear_normalizer(rule: _MetricRule, value: float) -> float:
    span = rule.maximum - rule.minimum
    if span <= 0:
        return 0.0
    fraction = (value - rule.minimum) / span
    if not rule.higher_is_better:
        fraction = 1.0 - fraction
    return _clamp(fraction * 100.0)


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _sign_normalizer(value: float) -> float:
    """Give a neutral result to zero and a directional result to profit."""

    if value > 0:
        return 100.0
    if value < 0:
        return 0.0
    return 50.0


_FUNDAMENTAL_RULES: Final[tuple[_MetricRule, ...]] = (
    _MetricRule("gross_margin", 0.30, 0.0, 0.90),
    _MetricRule("operating_margin", 0.30, -0.50, 0.60),
    _MetricRule("eps", 0.15, -5.0, 5.0),
    _MetricRule("net_income", 0.10, 0.0, 1.0, normalizer=_sign_normalizer),
    _MetricRule("free_cash_flow", 0.15, 0.0, 1.0, normalizer=_sign_normalizer),
)

_GROWTH_RULES: Final[tuple[_MetricRule, ...]] = (
    _MetricRule("revenue_growth", 0.40, -1.0, 2.0),
    _MetricRule("eps_growth", 0.30, -1.0, 2.0),
    _MetricRule("fcf_growth", 0.30, -1.0, 2.0),
)

_VALUATION_RULES: Final[tuple[_MetricRule, ...]] = (
    _MetricRule("pe", 0.40, 1.0, 100.0, higher_is_better=False),
    _MetricRule("forward_pe", 0.35, 1.0, 100.0, higher_is_better=False),
    _MetricRule("peg", 0.25, 0.1, 5.0, higher_is_better=False),
)

# This is a positive quality score (100 means lower observed risk), so it can
# participate in the overall score without changing the score direction.
_RISK_RULES: Final[tuple[_MetricRule, ...]] = (
    _MetricRule("operating_margin", 0.35, -0.50, 0.60),
    _MetricRule("gross_margin", 0.25, 0.0, 0.90),
    _MetricRule("revenue_growth", 0.20, -1.0, 2.0),
    _MetricRule("free_cash_flow", 0.20, 0.0, 1.0, normalizer=_sign_normalizer),
)

_OVERALL_RULES: Final[tuple[tuple[str, float], ...]] = (
    ("fundamental", 0.30),
    ("growth", 0.25),
    ("valuation", 0.25),
    ("risk", 0.20),
)


def _metric_value(metrics: FinancialMetrics, name: str) -> MetricValue | None:
    value = getattr(metrics, name)
    if value is None or value.value is None:
        return None
    return cast(MetricValue, value)


def _component_for(
    metrics: FinancialMetrics,
    rule: _MetricRule,
    missing: list[str],
    limitations: list[str],
) -> tuple[ScoreComponent | None, float | None]:
    metric = _metric_value(metrics, rule.name)
    if metric is None:
        missing.append(rule.name)
        return None, None

    raw_value = metric.value
    if raw_value is None or not isfinite(raw_value):
        missing.append(rule.name)
        limitations.append(f"{rule.name} is not finite and was excluded.")
        return None, None

    in_range = rule.minimum <= raw_value <= rule.maximum
    # Sign rules use a broad finite domain; their bounds are implementation
    # placeholders and should not reject a valid positive/negative amount.
    if rule.normalizer is not _sign_normalizer and not in_range:
        missing.append(rule.name)
        limitations.append(
            f"{rule.name}={raw_value:g} is outside the supported range "
            f"[{rule.minimum:g}, {rule.maximum:g}] and was excluded."
        )
        return None, None

    normalized = (
        rule.normalizer(raw_value)
        if rule.normalizer is not None
        else _linear_normalizer(rule, raw_value)
    )
    normalized = round(_clamp(normalized), 10)
    component = ScoreComponent(
        metric=rule.name,
        raw_value=raw_value,
        normalized_score=normalized,
        weight=rule.weight,
        contribution=normalized * rule.weight,
        source=metric.source,
        source_url=metric.source_url,
    )
    return component, normalized


def _confidence(available: int, expected: int) -> Literal["low", "medium", "high"]:
    if available == 0:
        return "low"
    if available == expected:
        return "high"
    if available * 2 >= expected:
        return "medium"
    return "low"


def _unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _build_breakdown(
    score_name: str,
    metrics: FinancialMetrics,
    rules: tuple[_MetricRule, ...],
) -> ScoreBreakdown:
    missing: list[str] = []
    limitations = list(metrics.limitations)
    candidates: list[tuple[ScoreComponent, float]] = []
    for rule in rules:
        component, normalized = _component_for(metrics, rule, missing, limitations)
        if component is not None and normalized is not None:
            candidates.append((component, normalized))

    total_weight = sum(component.weight for component, _ in candidates)
    components: list[ScoreComponent] = []
    weighted_score = 0.0
    if total_weight > 0:
        for component, normalized in candidates:
            weight = component.weight / total_weight
            contribution = normalized * weight
            weighted_score += contribution
            components.append(
                component.model_copy(
                    update={
                        "weight": weight,
                        "contribution": contribution,
                    }
                )
            )

    final_score = int(round(_clamp(weighted_score)))
    if missing:
        limitations.append(
            "Missing or invalid metrics were excluded; available weights were "
            "re-normalized."
        )
    return ScoreBreakdown(
        score_name=score_name,
        final_score=final_score,
        components=components,
        methodology_version=METHODOLOGY_VERSION,
        missing_metrics=_unique(missing),
        limitations=_unique(limitations),
        confidence=_confidence(len(components), len(rules)),
    )


def score_fundamental(metrics: FinancialMetrics) -> ScoreBreakdown:
    """Score profitability and cash-generation fundamentals."""

    return _build_breakdown("fundamental", metrics, _FUNDAMENTAL_RULES)


def score_growth(metrics: FinancialMetrics) -> ScoreBreakdown:
    """Score reported revenue, EPS, and free-cash-flow growth."""

    return _build_breakdown("growth", metrics, _GROWTH_RULES)


def score_valuation(metrics: FinancialMetrics) -> ScoreBreakdown:
    """Score valuation multiples; lower multiples receive higher scores."""

    return _build_breakdown("valuation", metrics, _VALUATION_RULES)


def score_risk(metrics: FinancialMetrics) -> ScoreBreakdown:
    """Score observable risk proxies as a positive quality score."""

    return _build_breakdown("risk", metrics, _RISK_RULES)


def score_overall(metrics: FinancialMetrics) -> ScoreBreakdown:
    """Combine the four independent scores with missing-category re-weighting."""

    category_scores = {
        "fundamental": score_fundamental(metrics),
        "growth": score_growth(metrics),
        "valuation": score_valuation(metrics),
        "risk": score_risk(metrics),
    }
    missing: list[str] = []
    limitations = list(metrics.limitations)
    available: list[tuple[str, float, ScoreBreakdown]] = []
    for category, configured_weight in _OVERALL_RULES:
        breakdown = category_scores[category]
        missing.extend(f"{category}.{name}" for name in breakdown.missing_metrics)
        limitations.extend(breakdown.limitations)
        if breakdown.components:
            available.append((category, configured_weight, breakdown))
        else:
            missing.append(category)

    total_weight = sum(weight for _, weight, _ in available)
    components: list[ScoreComponent] = []
    weighted_score = 0.0
    if total_weight > 0:
        for category, configured_weight, breakdown in available:
            weight = configured_weight / total_weight
            contribution = breakdown.final_score * weight
            weighted_score += contribution
            components.append(
                ScoreComponent(
                    metric=category,
                    raw_value=float(breakdown.final_score),
                    normalized_score=float(breakdown.final_score),
                    weight=weight,
                    contribution=contribution,
                    source=f"deterministic:{category}",
                )
            )

    if missing:
        limitations.append(
            "Missing score categories or metrics were excluded; available weights "
            "were re-normalized."
        )
    return ScoreBreakdown(
        score_name="overall",
        final_score=int(round(_clamp(weighted_score))),
        components=components,
        methodology_version=METHODOLOGY_VERSION,
        missing_metrics=_unique(missing),
        limitations=_unique(limitations),
        confidence=_confidence(len(components), len(_OVERALL_RULES)),
    )


def score_all(metrics: FinancialMetrics) -> dict[str, ScoreBreakdown]:
    """Return all named scores, including the aggregate score."""

    return {
        "fundamental": score_fundamental(metrics),
        "growth": score_growth(metrics),
        "valuation": score_valuation(metrics),
        "risk": score_risk(metrics),
        "overall": score_overall(metrics),
    }


class ScoringService:
    """Small dependency-free facade for callers that prefer a service object."""

    def score_fundamental(self, metrics: FinancialMetrics) -> ScoreBreakdown:
        return score_fundamental(metrics)

    def score_growth(self, metrics: FinancialMetrics) -> ScoreBreakdown:
        return score_growth(metrics)

    def score_valuation(self, metrics: FinancialMetrics) -> ScoreBreakdown:
        return score_valuation(metrics)

    def score_risk(self, metrics: FinancialMetrics) -> ScoreBreakdown:
        return score_risk(metrics)

    def score_overall(self, metrics: FinancialMetrics) -> ScoreBreakdown:
        return score_overall(metrics)

    def score_all(self, metrics: FinancialMetrics) -> dict[str, ScoreBreakdown]:
        return score_all(metrics)


# ``calculate_*`` names keep the public surface convenient for existing
# service callers while retaining one implementation of every rule.
calculate_fundamental_score = score_fundamental
calculate_growth_score = score_growth
calculate_valuation_score = score_valuation
calculate_risk_score = score_risk
calculate_overall_score = score_overall
