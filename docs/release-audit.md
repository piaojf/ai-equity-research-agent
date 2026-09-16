# Final Audit Report

## Scope

This audit covers the local Windows demo release only. No new product feature was added. Changes are limited to evidence-backed reliability, input validation, prompt-boundary, privacy, and release-packaging fixes.

## Findings and disposition

### Fixed

- SEC-001: LLM prompts now identify question, event, and SEC filing content as untrusted quoted data and prohibit following embedded instructions or revealing prompts/secrets.
- SEC-002: OpenAI-compatible LLM endpoints now require HTTPS and an allowlisted provider host (`api.deepseek.com` or `api.openai.com`).
- SEC-005: SEC Ask rejects unknown fields and unsupported filing types.
- SEC-006: request logs no longer serialize raw question/query content.
- ARC-003: real-mode SEC runtime rejects missing or blank SEC user-agent configuration.
- ARC-005: retrieval-only SEC responses are explicitly low confidence with a limitation.
- ARC-006: Yahoo history accepts zero volume while price fields remain strictly positive; malformed quote values map to provider errors.
- ARC-007: mock and durable deep-research jobs carry the originating request ID.
- QA invalid ticker cases: SEC Ask, Deep Research, and Research input paths reject invalid ticker values with the unified validation response.
- QA Qdrant cold-start race: collection initialization is single-flight per store instance.
- QA SEC failure: SEC evidence failure produces a low-confidence report with a limitation instead of leaving the workflow unhandled.
- Frontend failed-task state now displays the persisted error.
- Frontend browser API fallback is same-origin; production server-side backend URL remains explicit through `BACKEND_INTERNAL_URL`.
- Docker release packaging now includes Alembic files, runs migrations before service startup, and uses the frontend lockfile with `npm ci`.
- Historical local verification artifacts were removed from Git tracking and `work/` is ignored to prevent local path leakage.

### Accepted local-only limitations

- The local demo has no authentication or tenant ownership. It is not an internet-facing deployment.
- Rate limiting, queue quotas, stale-worker recovery, and atomic cross-process job claims remain production-hardening work.
- Real mode currently uses deterministic 32-dimensional embeddings; semantic embedding quality is not claimed as production-grade.
- API route composition still constructs some infrastructure dependencies directly; this is an architecture debt item, not changed in this audit.
- Docker was not built or started because local development uses native Windows services. The Linux Compose files were statically audited and migration packaging was corrected.

## Release gate

`RELEASE CANDIDATE READY — LOCAL ONLY`

The release is suitable for the local portfolio demo with PostgreSQL, Qdrant, Redis, ARQ, SEC, Yahoo, and DeepSeek configured. It is not a production deployment approval until authentication, rate limiting, semantic embeddings, and composition-root/deployment hardening are completed.
