# Deep Research Background Job

The public API is asynchronous:

```text
POST /api/deep-research -> HTTP 202 -> task_id -> GET status
```

The application boundary is:

```text
FastAPI -> ResearchTask(queued) -> TaskQueue -> Worker
                                      -> LangGraph Deep Research Workflow
                                      -> PostgreSQL DeepResearchReport
```

The workflow is a real LangGraph graph with evidence-first nodes for question
understanding, historical price retrieval, significant-move detection, news
and announcement search, optional SEC lookup, cause analysis, evidence
cross-checking and report generation. Conclusions retain `evidence_ids`.

Local tests use `InMemoryTaskQueue`. Production deployment should replace that
port with ARQ backed by Redis; the worker contract remains `run_once`, making
retries and process supervision explicit without placing work in the HTTP
request handler.
