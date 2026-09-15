from datetime import UTC, datetime

import pytest

from app.schemas.financial import FinancialMetrics, MetricValue
from app.scoring.service import (
    score_fundamental,
    score_growth,
    score_overall,
    score_risk,
    score_valuation,
)


def metric(name: str, value: float | None, source: str = "fixture") -> MetricValue:
    del name
    return MetricValue(
        value=value,
        source=source,
        retrieved_at=datetime(2026, 9, 15, tzinfo=UTC),
    )


@pytest.fixture()
def full_metrics() -> FinancialMetrics:
    return FinancialMetrics(
        ticker="TEST",
        currency="USD",
        revenue=metric("revenue", 1000),
        revenue_growth=metric("revenue_growth", 0.20),
        eps=metric("eps", 3.0),
        eps_growth=metric("eps_growth", 0.25),
        gross_margin=metric("gross_margin", 0.70),
        operating_margin=metric("operating_margin", 0.30),
        net_income=metric("net_income", 100),
        free_cash_flow=metric("free_cash_flow", 80),
        fcf_growth=metric("fcf_growth", 0.30),
        pe=metric("pe", 20),
        forward_pe=metric("forward_pe", 18),
        peg=metric("peg", 1.2),
    )


def assert_explainable(breakdown) -> None:  # noqa: ANN001 - schema under test
    assert 0 <= breakdown.final_score <= 100
    assert breakdown.methodology_version
    assert breakdown.confidence in {"low", "medium", "high"}
    assert sum(component.weight for component in breakdown.components) == pytest.approx(
        1
    )
    contributions = sum(component.contribution for component in breakdown.components)
    assert contributions == pytest.approx(breakdown.final_score, abs=1)
    for component in breakdown.components:
        assert component.raw_value is not None
        assert component.normalized_score is not None
        assert 0 <= component.normalized_score <= 100
        assert component.weight > 0
        assert component.contribution >= 0
        assert component.source


@pytest.mark.parametrize(
    "scorer",
    [score_fundamental, score_growth, score_valuation, score_risk, score_overall],
)
def test_scores_with_full_data_are_deterministic_and_explainable(
    scorer, full_metrics
) -> None:
    first = scorer(full_metrics)
    second = scorer(full_metrics)

    assert first == second
    assert first.missing_metrics == []
    assert_explainable(first)


def test_missing_metrics_are_excluded_and_weights_are_renormalized(
    full_metrics,
) -> None:
    partial = full_metrics.model_copy(update={"pe": None, "forward_pe": None})

    valuation = score_valuation(partial)

    assert valuation.missing_metrics == ["pe", "forward_pe"]
    assert [component.metric for component in valuation.components] == ["peg"]
    assert valuation.components[0].weight == pytest.approx(1)
    assert valuation.components[0].contribution == pytest.approx(
        valuation.components[0].normalized_score
    )
    assert valuation.final_score != 0


def test_invalid_ranges_are_excluded_without_leaving_score_bounds(full_metrics) -> None:
    invalid = full_metrics.model_copy(
        update={
            "gross_margin": metric("gross_margin", 1.5),
            "revenue_growth": metric("revenue_growth", 3.0),
            "pe": metric("pe", -2.0),
        }
    )

    fundamental = score_fundamental(invalid)
    growth = score_growth(invalid)
    valuation = score_valuation(invalid)

    assert "gross_margin" in fundamental.missing_metrics
    assert "revenue_growth" in growth.missing_metrics
    assert "pe" in valuation.missing_metrics
    assert all(
        0 <= score.final_score <= 100
        for score in (fundamental, growth, valuation)
    )
    assert all(
        "excluded" in limitation
        for score in (fundamental, growth, valuation)
        for limitation in score.limitations
    )


def test_overall_reweights_missing_categories(full_metrics) -> None:
    no_valuation = full_metrics.model_copy(
        update={"pe": None, "forward_pe": None, "peg": None}
    )

    overall = score_overall(no_valuation)

    assert "valuation" in overall.missing_metrics
    assert all(component.metric != "valuation" for component in overall.components)
    assert sum(component.weight for component in overall.components) == pytest.approx(1)
    assert_explainable(overall)
