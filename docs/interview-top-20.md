# Top 20 Technical Interview Questions

1. **Why separate providers?**  Vendor APIs change independently; interfaces
   keep services testable and make Yahoo/Finnhub/SEC replacements local.
2. **Why is SEC Company Facts separate from EDGAR?**  Company Facts is the
   normalized fundamentals source; EDGAR provides filing text and citations.
3. **Why not let the LLM score a stock?**  Numeric scoring needs reproducibility,
   auditability, and stable regression tests.
4. **How do you answer “why this score”?**  `ScoreBreakdown` exposes each raw
   metric, normalized score, weight, contribution, and source.
5. **How are missing metrics handled?**  Missing components are excluded and
   remaining weights are explicitly renormalized; missing data is not zero.
6. **Why use LangGraph?**  It makes agent steps explicit, stateful, bounded,
   and independently testable rather than hiding orchestration in prompts.
7. **What is the Deep Research boundary?**  The API accepts a request with 202,
   creates a task, queues work, and lets a worker persist the report.
8. **Why ARQ?**  It is a low-complexity Python/Redis choice; the queue contract
   allows Dramatiq or Celery later without changing API schemas.
9. **How do you avoid unsupported causal claims?**  Events carry evidence IDs,
   cross-checking deduplicates evidence, and no-evidence reports are low
   confidence with explicit limitations.
10. **Why not cite PDF pages?**  SEC HTML and filing revisions make accession,
    section, and chunk identity more stable than page numbers.
11. **What belongs in a citation?**  Ticker, filing type/date, accession number,
    section, chunk ID, source URL, excerpt, and optional page/anchor.
12. **Why have an in-memory vector store?**  It makes unit tests deterministic;
    Qdrant is selected behind the same vector-store protocol in deployment.
13. **How are external calls tested?**  Provider tests use local mock transports;
    integration tests are opt-in and the default suite has no external calls.
14. **How are errors exposed?**  Domain exceptions map to stable error codes,
    retryability, sanitized messages, and a request ID in `ErrorResponse`.
15. **How are requests correlated?**  Middleware accepts or creates a UUID-like
    request ID, stores it in context, returns it, and adds it to request logs.
16. **Why PostgreSQL repositories?**  Persistence is isolated from routes and
    services, with async sessions, transaction rollback, constraints, and
    Alembic migration history.
17. **What is the production network boundary?**  Nginx publishes ports 80/443;
    backend and stateful services use a private Docker Compose network.
18. **What happens when a provider is down?**  Services return sanitized domain
    errors or partial reports with limitations; they do not silently invent
    values or silently fall back in real mode.
19. **How do you keep scope controlled?**  Each phase has a contract, dependency
    DAG, tests, lint/type gates, diff review, and an explicit next-phase list.
20. **What would you build next?**  Durable ARQ task/report updates, authenticated
    SEC ingestion, real news integration, and frontend Node-based CI validation.
