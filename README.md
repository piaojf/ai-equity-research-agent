# SignalRoom AI · AI Equity Research Agent

[![CI](https://github.com/piaojf/ai-equity-research-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/piaojf/ai-equity-research-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

SignalRoom AI 是一个面向真实投研流程的证据优先美股研究工作台，也是 AI Agent Engineer / Forward Deployed Engineer 作品集项目。

它把市场行情、基本面、SEC 文件、可解释评分、RAG 检索和 Deep Research Agent 拆成可验证的工程边界：每个核心结论都尽量回到原始数据、引用和可复现的处理路径。

SignalRoom AI is an evidence-first US equity research workspace designed to demonstrate production-minded AI agent engineering, data integration, explainable scoring, retrieval, and deployment practices.

## 页面介绍

| 页面 | 入口 | 用途 |
| --- | --- | --- |
| 总览 | / | 查看研究工作台入口和示例股票 |
| 股票详情 | /stock/NVDA | 查看行情、评分拆解、财务数据和引用来源 |
| 股票对比 | /compare | 手动输入任意两家美股公司代码后进行比较 |
| SEC 研究问答 | /sec-ask | 在一个问题框中输入“研究 AAPL 的主要业务风险”并返回引用 |
| 深度研究 | /deep-research | 在一个问题框中输入标的和研究问题，异步生成研究报告 |

当前前端页面为中文本地演示界面，默认支持手动输入美股代码，不依赖固定的 NVDA / AMD 页面状态。

## 核心能力

- Provider Interface：行情、基本面、新闻、SEC EDGAR 均通过 Provider 边界接入。
- Deterministic Scoring：核心数字评分由确定性 Python 引擎计算，LLM 不决定分数。
- ScoreBreakdown：保存原始值、归一化分数、权重、贡献值和数据来源，可回答“为什么是这个分数”。
- SEC Citation：使用 ticker、filing type、filing date、accession number、section、chunk id、source URL 和 excerpt 追踪证据。
- SEC RAG：清洗 SEC Filing、切块、生成 embedding、写入 Qdrant，并进行引用感知检索。
- Agent Workflow：LangGraph 负责研究流程编排，DeepSeek V4.1 Flash 负责叙事层，不替代确定性计算。
- Background Job：FastAPI 返回 HTTP 202 和 task_id，Redis / ARQ Worker 执行异步 Deep Research，PostgreSQL 持久化任务和报告。
- Mock Mode：DATA_MODE=mock 可在没有真实 API Key 时启动，默认测试不访问外部 API。

## 系统架构

浏览器 → Next.js Dashboard → Nginx / HTTPS → FastAPI Backend

FastAPI → Provider Interfaces → Yahoo / Finnhub / SEC Company Facts / SEC EDGAR
FastAPI → Deterministic Scoring → ScoreBreakdown → ResearchReport
FastAPI → ResearchTask → Redis / ARQ → Worker → LangGraph Deep Research
Deep Research → Qdrant Retrieval + DeepSeek → PostgreSQL ResearchReport

生产目标为 Linux VPS + Docker Compose + Nginx + HTTPS，服务包括 nginx、frontend、backend、worker、postgres、qdrant 和 redis。Docker 是上线阶段配置，不是当前 Windows 本机研发的前置依赖。

## 本机开发

### 1. 创建环境

Windows PowerShell：

    py -3.12 -m venv .venv
    .venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
    Copy-Item .env.example .env

本地无真实数据源时，保持 .env 中 DATA_MODE=mock。真实模式需要填写相应 Provider Key，并连接 PostgreSQL、Redis 和 Qdrant。

### 2. 启动 Backend

    .venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000

### 3. 启动 Frontend

    cd frontend
    npm ci
    npm run dev

访问：

- http://127.0.0.1:3000
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/redoc

### 4. 启动本机 ARQ Worker（真实异步研究）

从项目根目录执行，确保 Worker 读取根目录 .env：

    $env:PYTHONPATH="$PWD\backend"
    .venv\Scripts\python.exe -m arq app.workers.entrypoint.WorkerSettings

Qdrant 本机运行地址为 http://127.0.0.1:6333，Redis 默认地址为 redis://localhost:6379/0。

## DeepSeek 配置

项目使用 DeepSeek 的 OpenAI-compatible API。API Key 只写入本机 .env，不要提交到 GitHub：

    DEEPSEEK_API_KEY=your-key
    DEEPSEEK_MODEL=deepseek-flash
    DEEPSEEK_BASE_URL=https://api.deepseek.com

DeepSeek 只负责研究叙事和结构化解释；核心数值评分仍由确定性引擎产生。

## 测试与质量检查

Backend：

    .venv\Scripts\python.exe -m pytest -q
    .venv\Scripts\ruff.exe check backend\app backend\tests
    .venv\Scripts\mypy.exe backend\app

Frontend：

    cd frontend
    npm run lint
    npm run typecheck
    npm run build

项目内的最终测试 Agent 位于 tools/final_test_agent.py，会执行质量检查和本地页面冒烟检查，并写入 reports/final-test-report.md。

## 项目结构

    backend/app/api             FastAPI 路由
    backend/app/core            配置、日志、request_id、错误处理
    backend/app/providers       行情、基本面、SEC 和新闻 Provider
    backend/app/scoring         确定性评分引擎
    backend/app/rag             SEC 清洗、切块、embedding 和 Qdrant
    backend/app/deep_research   Deep Research 图和运行时工厂
    backend/app/workers         Redis / ARQ Worker 入口
    frontend                    Next.js 中文研究工作台
    docs                        架构、接口、RAG、部署和演示文档
    deploy                      Linux 部署、备份和运维脚本
    nginx                       生产反向代理配置
    tools                       最终测试 Agent
    reports                     测试报告

## 生产部署

Linux VPS 上线阶段使用 Docker Compose，包含 Nginx、Frontend、Backend、Worker、PostgreSQL、Qdrant 和 Redis。请阅读 docs/deployment.md，完成环境变量、HTTPS、健康检查、日志和备份配置后再部署。

Vercel / Render 可以作为可选部署方式，但不是本项目的主要生产目标。

## 开源协作

欢迎提交 Issue、改进文档和 Pull Request。请先阅读 CONTRIBUTING.md。安全问题请按照 SECURITY.md 进行报告。

## 路线图

- 提升真实 Provider 的覆盖范围和缓存策略。
- 增强 SEC 检索质量评估和引用可视化。
- 完善 Worker 监控、重试、告警和生产运维。
- 继续改进 Linux VPS 部署和可观测性。

## 免责声明

本项目仅用于工程展示、研究和教育，不构成投资建议。任何生成式分析都应由用户独立核验。

## License

MIT License，详见 LICENSE。
