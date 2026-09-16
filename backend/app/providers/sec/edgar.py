from __future__ import annotations

from datetime import date
from typing import Any

import httpx
from pydantic import HttpUrl, SecretStr, TypeAdapter

from app.providers.exceptions import (
    InvalidTickerError,
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from app.providers.fundamentals.errors import SECDataUnavailableError
from app.providers.sec.base import FilingMetadata, SECProvider


class SECEDGARProvider(SECProvider):
    """Small SEC submissions and filing-text adapter with sanitized failures."""

    name = "sec_edgar"
    submissions_url = "https://data.sec.gov/submissions/CIK{cik}.json"
    ticker_url = "https://www.sec.gov/files/company_tickers.json"

    def __init__(
        self,
        user_agent: SecretStr | str | None,
        *,
        ticker_ciks: dict[str, str | int] | None = None,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        value = (
            user_agent.get_secret_value()
            if isinstance(user_agent, SecretStr)
            else user_agent
        )
        if not value or not value.strip():
            raise ProviderConfigurationError("SEC_USER_AGENT is required.")
        self.user_agent = value.strip()
        self.timeout_seconds = timeout_seconds
        self._client = client
        self._ticker_ciks = {
            key.strip().upper(): str(cik).zfill(10)
            for key, cik in (ticker_ciks or {}).items()
        }
        self._ticker_directory_loaded = False

    async def _get_json(self, url: str) -> dict[str, Any]:
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        try:
            if self._client is not None:
                response = await self._client.get(url, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.get(url, headers=headers)
            if response.status_code == 429:
                raise ProviderRateLimitError(self.name)
            if response.status_code >= 500:
                raise SECDataUnavailableError()
            response.raise_for_status()
            payload = response.json()
        except (ProviderRateLimitError, SECDataUnavailableError):
            raise
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(self.name) from exc
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            raise SECDataUnavailableError() from exc
        if not isinstance(payload, dict):
            raise SECDataUnavailableError("SEC returned an invalid payload.")
        return payload

    async def _resolve_cik(self, ticker: str) -> str:
        normalized = ticker.strip().upper()
        if normalized.isdigit():
            return normalized.zfill(10)
        if normalized in self._ticker_ciks:
            return self._ticker_ciks[normalized]

        if not self._ticker_directory_loaded:
            payload = await self._get_json(self.ticker_url)
            self._load_ticker_directory(payload)
            self._ticker_directory_loaded = True
        if normalized in self._ticker_ciks:
            return self._ticker_ciks[normalized]
        raise InvalidTickerError(normalized)

    def _load_ticker_directory(self, payload: dict[str, Any]) -> None:
        for entry in payload.values():
            if not isinstance(entry, dict):
                continue
            entry_ticker = entry.get("ticker")
            raw_cik = entry.get("cik_str", entry.get("cik"))
            if isinstance(entry_ticker, str) and isinstance(raw_cik, (str, int)):
                cik = str(raw_cik).strip()
                if cik.isdigit() and len(cik) <= 10:
                    self._ticker_ciks[entry_ticker.strip().upper()] = cik.zfill(10)

    async def list_filings(
        self, ticker: str, forms: list[str]
    ) -> list[FilingMetadata]:
        cik = await self._resolve_cik(ticker)
        payload = await self._get_json(self.submissions_url.format(cik=cik))
        recent = payload.get("filings", {}).get("recent")
        if not isinstance(recent, dict):
            raise SECDataUnavailableError("SEC submissions omitted recent filings.")
        allowed = {form.upper() for form in forms}
        result: list[FilingMetadata] = []
        forms_data = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        documents = recent.get("primaryDocument", [])
        for index, form in enumerate(forms_data):
            if not isinstance(form, str) or form.upper() not in allowed:
                continue
            try:
                filed = date.fromisoformat(str(dates[index]))
                accession = str(accessions[index])
                document = str(documents[index])
            except (IndexError, TypeError, ValueError) as exc:
                raise SECDataUnavailableError(
                    "SEC filing metadata was malformed."
                ) from exc
            accession_path = accession.replace("-", "")
            url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                f"{accession_path}/{document}"
            )
            result.append(
                FilingMetadata(
                    ticker=ticker.strip().upper(),
                    filing_type=form,
                    filing_date=filed,
                    accession_number=accession,
                    source_url=TypeAdapter(HttpUrl).validate_python(url),
                )
            )
        return result

    async def fetch_filing(self, filing: FilingMetadata) -> str:
        url = str(filing.source_url)
        headers = {"User-Agent": self.user_agent, "Accept": "text/html"}
        try:
            if self._client is not None:
                response = await self._client.get(url, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.get(url, headers=headers)
            if response.status_code == 429:
                raise ProviderRateLimitError(self.name)
            if response.status_code >= 500:
                raise SECDataUnavailableError()
            response.raise_for_status()
            return response.text
        except (ProviderRateLimitError, SECDataUnavailableError):
            raise
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(self.name) from exc
        except httpx.HTTPError as exc:
            raise SECDataUnavailableError() from exc
