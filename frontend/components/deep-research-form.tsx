"use client";

import { useEffect, useState } from "react";

import { getDeepResearch, submitDeepResearch } from "../lib/api";
import type { DeepResearchTask } from "../lib/types";

const DEFAULT_TICKER = "NVDA";
const TICKER_PATTERN = /^[A-Z][A-Z0-9.-]{0,9}$/;
const statusText: Record<DeepResearchTask["status"], string> = {
  queued: "排队中",
  running: "执行中",
  completed: "已完成",
  failed: "失败",
};

function normalizeTicker(value: string): string {
  return value.trim().toUpperCase();
}

export function DeepResearchForm({ initialTicker = DEFAULT_TICKER }: { initialTicker?: string }) {
  const [ticker, setTicker] = useState(normalizeTicker(initialTicker) || DEFAULT_TICKER);
  const [question, setQuestion] = useState("最近有哪些重大事项？");
  const [task, setTask] = useState<DeepResearchTask | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!task || task.status === "completed" || task.status === "failed") return;
    const timer = window.setInterval(async () => {
      try {
        setTask(await getDeepResearch(task.task_id));
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "任务状态查询失败。");
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [task]);

  async function submit() {
    const normalizedTicker = normalizeTicker(ticker);
    if (!normalizedTicker) {
      setError("请输入股票代码，例如 NVDA 或 INTC。");
      return;
    }
    if (!TICKER_PATTERN.test(normalizedTicker)) {
      setError("股票代码格式不正确，请输入美股代码，例如 NVDA 或 BRK.B。");
      return;
    }
    if (!question.trim()) {
      setError("请输入研究问题。");
      return;
    }

    setLoading(true);
    setError(null);
    setTask(null);
    try {
      const accepted = await submitDeepResearch({ ticker: normalizedTicker, question: question.trim() });
      setTicker(normalizedTicker);
      setTask({ task_id: accepted.task_id, status: accepted.status });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "深度研究提交失败。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card stack">
      <div className="section-heading">
        <div>
          <span className="eyebrow">研究任务</span>
          <h2>研究 {ticker || "美股"} 的近期情况</h2>
        </div>
        <span className="tag amber">异步执行</span>
      </div>
      <div className="research-dialog" role="group" aria-label="深度研究对话框">
        <div className="dialog-header">
          <div>
            <span className="dialog-label">研究对话</span>
            <p>告诉我你想研究哪家公司，以及最想了解的问题。</p>
          </div>
          <span className="tag cyan">支持所有美股代码</span>
        </div>
        <div className="dialog-context">
          <span className="context-label">研究标的</span>
          <input
            id="deep-ticker"
            aria-label="研究标的"
            placeholder="输入股票代码，例如 NVDA、QCOM"
            value={ticker}
            onChange={(event) => setTicker(event.target.value.toUpperCase())}
            maxLength={10}
            autoCapitalize="characters"
            spellCheck={false}
          />
        </div>
        <textarea
          id="deep-question"
          aria-label="研究问题"
          placeholder="例如：最近有哪些重大事项？公司的主要业务风险是什么？"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          style={{ minHeight: 112 }}
        />
        <div className="dialog-footer">
          <span className="dialog-hint">一个问题，一次完整研究。</span>
          <div className="form-actions">
            <button className="button" type="button" onClick={submit} disabled={loading}>
              {loading ? "创建任务中…" : "开始深度研究"}
            </button>
            {task && <span className="tag cyan">任务：{statusText[task.status]}</span>}
          </div>
        </div>
      </div>
      {error && <div className="error-box"><strong>任务出现问题</strong><p>{error}</p></div>}
      {task && (
        <div className="signal">
          <div className="quick-links">
            <span className="tag">{statusText[task.status]}</span>
            <span className="tag cyan">任务 ID：{task.task_id.slice(0, 8)}…</span>
          </div>
          {task.status === "failed" ? (
            <div className="error-box">
              <strong>任务失败</strong>
              <p>{task.error ?? "后台任务执行失败。"}</p>
            </div>
          ) : task.report ? (
            <>
              <h2 style={{ marginTop: 18 }}>
                {task.report.confidence === "high" ? "高可信度" : task.report.confidence === "medium" ? "中等可信度" : "低可信度"}
              </h2>
              <p style={{ lineHeight: 1.8 }}>{task.report.conclusion}</p>
              <p className="muted">{task.report.evidence.length} 条证据 · {task.report.major_events.length} 个重要事件</p>
            </>
          ) : <p className="muted">任务已接受，系统正在轮询后台状态。</p>}
        </div>
      )}
    </section>
  );
}
