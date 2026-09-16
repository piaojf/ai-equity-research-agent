from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any

import httpx
from pydantic import HttpUrl, SecretStr, TypeAdapter

from app.providers.exceptions import (
    InvalidTickerError,
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from app.providers.fundamentals.base import FinancialDataProvider
from app.providers.fundamentals.errors import SECDataUnavailableError
from app.schemas.financial import FinancialMetrics, MetricValue


@dataclass(frozen=True)
class _AnnualFact:
    value: float
    end: date
    filed: date
    unit: str


class SECCompanyFactsProvider(FinancialDataProvider):
    """Normalize SEC Company Facts into the shared financial schema.

    SEC Company Facts does not contain market prices or analyst estimates, so
    valuation metrics are deliberately left null rather than inferred.
    """

    name = "sec_company_facts"
    facts_base_url = "https://data.sec.gov/api/xbrl/companyfacts"
    ticker_url = "https://www.sec.gov/files/company_tickers.json"
    _TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")

    _REVENUE_TAGS = (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    )
    _EPS_TAGS = ("EarningsPerShareDiluted", "EarningsPerShareBasic")
    _GROSS_PROFIT_TAGS = ("GrossProfit",)
    _OPERATING_INCOME_TAGS = (
        "OperatingIncomeLoss",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    )
    _NET_INCOME_TAGS = ("NetIncomeLoss", "ProfitLoss")
    _OPERATING_CASH_FLOW_TAGS = (
        "NetCashProvidedByUsedInOperatingActivities",
    )
    _CAPEX_TAGS = (
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    )
    _ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
    _INTERIM_FORMS = {"10-Q", "10-Q/A", "6-K", "6-K/A"}

    def __init__(
        self,
        user_agent: SecretStr | str | None = None,
        *,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
        ticker_ciks: Mapping[str, str | int] | None = None,
        cik: str | int | None = None,
    ) -> None:
        agent = (
            user_agent.get_secret_value()
            if isinstance(user_agent, SecretStr)
            else user_agent
        )
        if not agent or not agent.strip():
            raise ProviderConfigurationError(
                "SEC_USER_AGENT is required for SEC Company Facts."
            )
        if timeout_seconds <= 0:
            raise ProviderConfigurationError("SEC provider timeout must be positive.")
        self.user_agent = agent.strip()
        self.timeout_seconds = timeout_seconds
        self._client = client
        self._ticker_ciks = {
            key.strip().upper(): self._normalize_cik(value)
            for key, value in (ticker_ciks or {}).items()
        }
        self._fixed_cik = self._normalize_cik(cik) if cik is not None else None

    @property
    def source_url(self) -> HttpUrl:
        return TypeAdapter(HttpUrl).validate_python(self.facts_base_url)

    def _facts_url(self, cik: str) -> HttpUrl:
        return TypeAdapter(HttpUrl).validate_python(
            f"{self.facts_base_url}/CIK{cik}.json"
        )

    @staticmethod
    def _normalize_cik(value: str | int) -> str:
        text = str(value).strip()
        if not text.isdigit() or len(text) > 10:
            raise ProviderConfigurationError("SEC CIK must contain up to 10 digits.")
        return text.zfill(10)

    async def _request_json(self, url: str) -> dict[str, Any]:
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        try:
            if self._client is not None:
                response = await self._client.get(url, headers=headers)
                return self._decode_response(response)
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, headers=headers)
                return self._decode_response(response)
        except (ProviderRateLimitError, ProviderTimeoutError, SECDataUnavailableError):
            raise
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(self.name) from exc
        except httpx.HTTPError as exc:
            raise SECDataUnavailableError() from exc
        except (TypeError, ValueError) as exc:
            raise SECDataUnavailableError("SEC returned malformed JSON.") from exc

    def _decode_response(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code == 429:
            raise ProviderRateLimitError(self.name)
        if response.status_code >= 500:
            raise SECDataUnavailableError()
        try:
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise SECDataUnavailableError() from exc
        except (TypeError, ValueError) as exc:
            raise SECDataUnavailableError("SEC returned malformed JSON.") from exc
        if not isinstance(payload, dict):
            raise SECDataUnavailableError("SEC returned an invalid payload.")
        return payload

    async def _resolve_cik(self, ticker: str) -> str:
        if self._fixed_cik is not None:
            return self._fixed_cik
        if ticker.isdigit():
            return self._normalize_cik(ticker)
        if ticker in self._ticker_ciks:
            return self._ticker_ciks[ticker]

        payload = await self._request_json(self.ticker_url)
        for entry in payload.values():
            if not isinstance(entry, dict):
                continue
            entry_ticker = entry.get("ticker")
            if isinstance(entry_ticker, str) and entry_ticker.strip().upper() == ticker:
                raw_cik = entry.get("cik_str", entry.get("cik"))
                if isinstance(raw_cik, (str, int)):
                    try:
                        return self._normalize_cik(raw_cik)
                    except ProviderConfigurationError as exc:
                        raise SECDataUnavailableError(
                            "SEC ticker mapping was malformed."
                        ) from exc
        raise InvalidTickerError(ticker)

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not isinstance(value, str):
            return None
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None

    @staticmethod
    def _number(value: Any) -> float | None:
        if isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    @classmethod
    def _unit_rank(cls, unit: str, *, eps: bool) -> tuple[int, str]:
        normalized = unit.strip().upper()
        if eps:
            preferred = ("USD/SHARES", "USD/SHARE")
            return (0 if normalized in preferred else 1, normalized)
        return (0 if "/" not in normalized and normalized == "USD" else 1, normalized)

    @classmethod
    def _annual_facts(
        cls,
        payload: dict[str, Any],
        tags: tuple[str, ...],
        *,
        eps: bool = False,
    ) -> list[_AnnualFact]:
        facts = payload.get("facts")
        if not isinstance(facts, dict):
            raise SECDataUnavailableError("SEC payload omitted facts.")
        us_gaap = facts.get("us-gaap")
        if not isinstance(us_gaap, dict):
            return []

        for tag in tags:
            candidate = us_gaap.get(tag)
            if not isinstance(candidate, dict) or not isinstance(
                candidate.get("units"), dict
            ):
                continue
            units = candidate["units"]
            valid_units = [unit for unit in units if isinstance(unit, str)]
            valid_units.sort(key=lambda unit: cls._unit_rank(unit, eps=eps))
            annual_records: list[_AnnualFact] = []
            interim_records: list[_AnnualFact] = []
            for unit in valid_units:
                raw_records = units.get(unit)
                if not isinstance(raw_records, list):
                    continue
                for raw in raw_records:
                    if not isinstance(raw, dict):
                        continue
                    value = cls._number(raw.get("val"))
                    end = cls._parse_date(raw.get("end"))
                    if value is None or end is None:
                        continue
                    filed = cls._parse_date(raw.get("filed"))
                    if filed is None:
                        continue
                    start = cls._parse_date(raw.get("start"))
                    duration = (end - start).days if start is not None else None
                    form = str(raw.get("form", "")).upper()
                    record = _AnnualFact(value, end, filed, unit)
                    if form in cls._ANNUAL_FORMS and (
                        duration is None or duration >= 270
                    ):
                        annual_records.append(record)
                    elif form in cls._INTERIM_FORMS and (
                        duration is None or duration > 0
                    ):
                        interim_records.append(record)
            if annual_records:
                return cls._deduplicate(annual_records)
            if interim_records:
                return cls._deduplicate(interim_records)
        return []

    @staticmethod
    def _deduplicate(records: list[_AnnualFact]) -> list[_AnnualFact]:
        latest_by_end: dict[date, _AnnualFact] = {}
        for record in records:
            previous = latest_by_end.get(record.end)
            if previous is None or record.filed >= previous.filed:
                latest_by_end[record.end] = record
        return sorted(latest_by_end.values(), key=lambda record: record.end)

    @staticmethod
    def _as_of(end: date) -> datetime:
        return datetime.combine(end, time.min, tzinfo=UTC)

    @staticmethod
    def _growth(values: list[_AnnualFact]) -> tuple[float, date] | None:
        if len(values) < 2 or values[-2].value == 0:
            return None
        return values[-1].value / values[-2].value - 1.0, values[-1].end

    def _metric(
        self,
        value: float,
        end: date,
        source_url: HttpUrl,
        retrieved_at: datetime,
    ) -> MetricValue:
        return MetricValue(
            value=value,
            source=self.name,
            source_url=source_url,
            as_of=self._as_of(end),
            retrieved_at=retrieved_at,
        )

    async def get_financials(self, ticker: str) -> FinancialMetrics:
        normalized = ticker.strip().upper()
        if not normalized or (
            not normalized.isdigit() and not self._TICKER_PATTERN.fullmatch(normalized)
        ):
            raise InvalidTickerError(normalized)
        cik = await self._resolve_cik(normalized)
        facts_url = self._facts_url(cik)
        payload = await self._request_json(str(facts_url))
        retrieved_at = datetime.now(UTC)

        revenue = self._annual_facts(payload, self._REVENUE_TAGS)
        eps = self._annual_facts(payload, self._EPS_TAGS, eps=True)
        gross_profit = self._annual_facts(payload, self._GROSS_PROFIT_TAGS)
        operating_income = self._annual_facts(payload, self._OPERATING_INCOME_TAGS)
        net_income = self._annual_facts(payload, self._NET_INCOME_TAGS)
        operating_cash_flow = self._annual_facts(
            payload, self._OPERATING_CASH_FLOW_TAGS
        )
        capex = self._annual_facts(payload, self._CAPEX_TAGS)

        limitations: list[str] = []
        source_url = facts_url

        def missing(metric: str, reason: str) -> None:
            limitations.append(f"{metric} is unavailable: {reason}.")

        def raw_metric(
            metric: str, values: list[_AnnualFact]
        ) -> MetricValue | None:
            if not values:
                missing(
                    metric,
                    "SEC Company Facts did not provide a usable annual fact",
                )
                return None
            latest = values[-1]
            return self._metric(latest.value, latest.end, source_url, retrieved_at)

        revenue_value = raw_metric("revenue", revenue)
        eps_value = raw_metric("eps", eps)
        net_income_value = raw_metric("net_income", net_income)

        revenue_growth: MetricValue | None = None
        growth = self._growth(revenue)
        if growth is None:
            missing("revenue_growth", "two usable annual revenue facts are required")
        else:
            revenue_growth = self._metric(
                growth[0], growth[1], source_url, retrieved_at
            )

        eps_growth: MetricValue | None = None
        growth = self._growth(eps)
        if growth is None:
            missing("eps_growth", "two usable annual EPS facts are required")
        else:
            eps_growth = self._metric(growth[0], growth[1], source_url, retrieved_at)

        def ratio_metric(
            metric: str,
            numerator: list[_AnnualFact],
            denominator: list[_AnnualFact],
        ) -> MetricValue | None:
            denominator_by_end = {item.end: item for item in denominator}
            common = [item for item in numerator if item.end in denominator_by_end]
            if not common:
                missing(
                    metric,
                    "matching annual numerator and revenue facts are required",
                )
                return None
            latest = common[-1]
            revenue_item = denominator_by_end[latest.end]
            if latest.unit.strip().upper() != revenue_item.unit.strip().upper():
                missing(metric, "matching annual facts use incompatible units")
                return None
            if revenue_item.value == 0:
                missing(metric, "the matching annual revenue fact is zero")
                return None
            return self._metric(
                latest.value / revenue_item.value,
                latest.end,
                source_url,
                retrieved_at,
            )

        gross_margin = ratio_metric("gross_margin", gross_profit, revenue)
        operating_margin = ratio_metric("operating_margin", operating_income, revenue)

        fcf_by_end: dict[date, tuple[float, str]] = {}
        capex_by_end = {item.end: item for item in capex}
        for cash_flow in operating_cash_flow:
            capital_spend = capex_by_end.get(cash_flow.end)
            if capital_spend is not None:
                if cash_flow.unit.strip().upper() != capital_spend.unit.strip().upper():
                    continue
                fcf_by_end[cash_flow.end] = (
                    cash_flow.value + capital_spend.value
                    if capital_spend.value < 0
                    else cash_flow.value - capital_spend.value,
                    cash_flow.unit,
                )
        if operating_cash_flow and capex and not fcf_by_end:
            missing("free_cash_flow", "matching annual facts use incompatible units")
        fcf_values = sorted(fcf_by_end.items())
        free_cash_flow: MetricValue | None = None
        fcf_growth: MetricValue | None = None
        if not fcf_values:
            missing(
                "free_cash_flow",
                "matching annual operating cash flow and capital expenditure "
                "facts are required",
            )
            missing("fcf_growth", "two usable annual free cash flow facts are required")
        else:
            latest_end, (latest_fcf, _) = fcf_values[-1]
            free_cash_flow = self._metric(
                latest_fcf, latest_end, source_url, retrieved_at
            )
            if len(fcf_values) < 2 or fcf_values[-2][1][0] == 0:
                missing(
                    "fcf_growth",
                    "two usable annual free cash flow facts are required",
                )
            else:
                previous_fcf = fcf_values[-2][1][0]
                fcf_growth = self._metric(
                    latest_fcf / previous_fcf - 1.0,
                    latest_end,
                    source_url,
                    retrieved_at,
                )

        currency: str | None = None
        for collection in (revenue, net_income, operating_cash_flow):
            if collection:
                currency = collection[-1].unit.split("/", 1)[0]
                break

        for metric in ("pe", "forward_pe", "peg"):
            missing(metric, "SEC Company Facts does not provide this metric")

        return FinancialMetrics(
            ticker=normalized,
            currency=currency,
            revenue=revenue_value,
            revenue_growth=revenue_growth,
            eps=eps_value,
            eps_growth=eps_growth,
            gross_margin=gross_margin,
            operating_margin=operating_margin,
            net_income=net_income_value,
            free_cash_flow=free_cash_flow,
            fcf_growth=fcf_growth,
            pe=None,
            forward_pe=None,
            peg=None,
            limitations=limitations,
        )


SECCompanyFactsAdapter = SECCompanyFactsProvider
