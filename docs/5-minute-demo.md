# Five-Minute Demo Script

The demo uses deterministic mock data and does not require API keys, a database,
Redis, Qdrant, Docker, or internet access.

## 0:00-1:00 - Start and prove the foundation

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
Invoke-RestMethod http://127.0.0.1:8000/health
```

Point out `status=ok`, `data_mode=mock`, and the top-level `request_id`. Open
`/docs` and show the typed API surface.

## 1:00-2:00 - Show market data and provider isolation

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/stocks/NVDA
```

Show the quote, historical points, source, retrieval time, and delayed-data
flag. Explain that the route calls `MarketService`, not a vendor SDK directly;
the registry can select a mock or real adapter.

## 2:00-3:00 - Explain the score

Open the stock detail route at `/stock/NVDA` and show the Score Breakdown card.
Then open `docs/shared-contracts.md` and point to `raw_value`,
`normalized_score`, `weight`, `contribution`, and `source`. State the core rule:
the LLM may explain a score but never calculates or mutates it.

## 3:00-4:00 - Show evidence and background research contracts

Open `/sec-ask` to show the low-confidence empty state. Explain that a future
answer must include ticker, filing type/date, accession number, section, chunk
ID, URL, and excerpt. Open `/deep-research` to show the queued state and the
workflow stages. The API contract is:

```text
POST /api/deep-research -> 202 + task_id
GET  /api/deep-research/{task_id} -> status/report
```

## 4:00-5:00 - Close with production architecture

Open `docker-compose.yml` and `docs/deployment.md`. Explain the Linux VPS
target: Nginx is the only public entry point; frontend, backend, worker,
PostgreSQL, Qdrant, and Redis stay on the private network. Finish with the
quality gate:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\ruff.exe check backend\app backend\tests
.venv\Scripts\mypy.exe backend\app
```

Conclude with the tradeoff: local development stays fast and deterministic,
while the production topology preserves a realistic deployment boundary.
