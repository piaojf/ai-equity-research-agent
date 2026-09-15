# Frontend Dashboard

The frontend is a Next.js, TypeScript and Tailwind dashboard organized around
data, score, evidence and research rather than a chat clone.

Pages:

- `/`: landing page and quick tickers.
- `/stock/[ticker]`: price, score breakdown, financial context and research links.
- `/compare`: side-by-side metrics and deterministic scores.
- `/sec-ask`: citation-aware filing question UI with low-confidence empty state.
- `/deep-research`: queued/running/completed/failed task presentation.

The current static mock presentation is runnable once Node.js dependencies are
installed. API integration uses `NEXT_PUBLIC_API_BASE_URL`; the backend remains
the source of truth for scores, citations and task state.
