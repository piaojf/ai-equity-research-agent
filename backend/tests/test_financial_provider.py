from datetime import UTC, datetime

import httpx
import pytest

from app.providers.exceptions import ProviderTimeoutError
from app.providers.fundamentals.sec_company_facts import SECCompanyFactsProvider


def _annual(value: float, year: int, *, filed: str | None = None) -> dict[str, object]:
    return {
        "fy": year,
        "fp": "FY",
        "form": "10-K",
        "filed": filed or f"{year + 1}-02-01",
        "start": f"{year}-01-01",
        "end": f"{year}-12-31",
        "val": value,
    }


def _facts_payload() -> dict[str, object]:
    def usd(tag: str, values: list[dict[str, object]]) -> tuple[str, dict[str, object]]:
        return tag, {"units": {"USD": values}}

    facts: dict[str, dict[str, object]] = dict(
        [
            usd(
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                [_annual(100, 2023), _annual(120, 2024)],
            ),
            usd("EarningsPerShareDiluted", [_annual(2, 2023), _annual(2.5, 2024)]),
            usd("GrossProfit", [_annual(40, 2023), _annual(48, 2024)]),
            usd("OperatingIncomeLoss", [_annual(20, 2023), _annual(24, 2024)]),
            usd("NetIncomeLoss", [_annual(10, 2023), _annual(15, 2024)]),
            usd(
                "NetCashProvidedByUsedInOperatingActivities",
                [_annual(30, 2023), _annual(40, 2024)],
            ),
            usd(
                "PaymentsToAcquirePropertyPlantAndEquipment",
                [_annual(5, 2023), _annual(8, 2024)],
            ),
        ]
    )
    # EPS is reported in a per-share unit in the SEC payload.
    facts["EarningsPerShareDiluted"] = {
        "units": {"USD/shares": [_annual(2, 2023), _annual(2.5, 2024)]}
    }
    return {"entityName": "Example Corp", "facts": {"us-gaap": facts}}


@pytest.mark.asyncio
async def test_sec_company_facts_normalizes_metrics_without_network() -> None:
    requested: list[str] = []

    def response(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, json=_facts_payload())

    client = httpx.AsyncClient(transport=httpx.MockTransport(response))
    provider = SECCompanyFactsProvider(
        "research@example.test",
        cik=320193,
        client=client,
    )

    metrics = await provider.get_financials("aapl")
    await client.aclose()

    assert requested == [
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"
    ]
    assert metrics.ticker == "AAPL"
    assert metrics.currency == "USD"
    assert metrics.revenue is not None
    assert metrics.revenue.value == 120.0
    assert metrics.revenue_growth is not None
    assert metrics.revenue_growth.value == pytest.approx(0.2)
    assert metrics.eps is not None
    assert metrics.eps.value == 2.5
    assert metrics.eps_growth is not None
    assert metrics.eps_growth.value == pytest.approx(0.25)
    assert metrics.gross_margin is not None
    assert metrics.gross_margin.value == pytest.approx(0.4)
    assert metrics.operating_margin is not None
    assert metrics.operating_margin.value == pytest.approx(0.2)
    assert metrics.net_income is not None
    assert metrics.net_income.value == 15.0
    assert metrics.free_cash_flow is not None
    assert metrics.free_cash_flow.value == 32.0
    assert metrics.fcf_growth is not None
    assert metrics.fcf_growth.value == pytest.approx(0.28)
    assert metrics.pe is None
    assert metrics.forward_pe is None
    assert metrics.peg is None
    assert {"pe", "forward_pe", "peg"} <= {
        limitation.split(" ", 1)[0] for limitation in metrics.limitations
    }

    for metric_name in (
        "revenue",
        "revenue_growth",
        "eps",
        "eps_growth",
        "gross_margin",
        "operating_margin",
        "net_income",
        "free_cash_flow",
        "fcf_growth",
    ):
        metric = getattr(metrics, metric_name)
        assert metric is not None
        assert metric.source == "sec_company_facts"
        assert metric.source_url is not None
        assert metric.as_of == datetime(2024, 12, 31, tzinfo=UTC)
        assert metric.retrieved_at.tzinfo == UTC


@pytest.mark.asyncio
async def test_sec_company_facts_maps_timeout_to_provider_error() -> None:
    def timeout(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("transport timeout")

    client = httpx.AsyncClient(transport=httpx.MockTransport(timeout))
    provider = SECCompanyFactsProvider(
        "research@example.test",
        cik="320193",
        client=client,
    )

    with pytest.raises(ProviderTimeoutError) as error:
        await provider.get_financials("AAPL")
    await client.aclose()

    assert "transport timeout" not in str(error.value)
