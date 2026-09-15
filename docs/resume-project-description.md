# Resume Project Description

## 中文版

**AI Equity Research Agent | Python, FastAPI, LangGraph, PostgreSQL, SEC EDGAR, Qdrant, Redis, Next.js**

- 设计并实现证据优先的美股研究平台，使用 Provider Interface 解耦行情、SEC Company Facts、SEC EDGAR 与新闻数据源，支持 `DATA_MODE=mock` 的无密钥本地开发。
- 构建确定性 Explainable Scoring Engine，输出 revenue growth、EPS growth、FCF growth 等 ScoreBreakdown，保留 raw value、归一化分数、权重、贡献值与来源，避免 LLM 参与核心数值决策。
- 使用 LangGraph 编排结构化 Equity Research 与 Deep Research Workflow，通过 HTTP 202、ResearchTask、Redis/ARQ Worker 边界处理长任务，并以证据 ID 关联重大事件与结论。
- 实现 SEC Filing RAG 设计，采用 accession number、section、chunk ID 和 excerpt 的 Citation Schema，使用 Qdrant 向量存储边界与低置信度空结果。
- 建立 PostgreSQL/Alembic 持久化模型、统一 ErrorResponse、request ID 与结构化请求日志，并完成 Linux VPS Docker Compose、Nginx、HTTPS、健康检查和备份方案。

## English version

**AI Equity Research Agent | Python, FastAPI, LangGraph, PostgreSQL, SEC EDGAR, Qdrant, Redis, Next.js**

- Designed and implemented an evidence-first US equity research platform with provider interfaces for market prices, SEC Company Facts, SEC EDGAR filings, and news, including keyless deterministic local mock mode.
- Built a deterministic explainable scoring engine that exposes revenue growth, EPS growth, and FCF growth breakdowns with raw values, normalized scores, weights, contributions, and source metadata; LLM output cannot change core numeric scores.
- Orchestrated structured equity research and Deep Research workflows with LangGraph and an HTTP 202 task boundary, Redis/ARQ worker entry point, evidence-linked events, and confidence-aware reports.
- Implemented a citation-aware SEC Filing RAG boundary using accession number, section, chunk ID, excerpt, deterministic test embeddings, and Qdrant-compatible vector storage.
- Established async PostgreSQL/Alembic persistence, unified error responses, request correlation IDs, structured request logs, and a Linux VPS Docker Compose/Nginx/HTTPS deployment design with health checks and backups.

## Interview positioning

Emphasize the contracts and failure boundaries rather than claiming provider
coverage: the project demonstrates how to make agentic research inspectable,
testable, deployable, and replaceable one integration at a time.
