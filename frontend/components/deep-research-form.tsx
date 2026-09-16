"use client";

import { useEffect, useState } from "react";

import { getDeepResearch, submitDeepResearch } from "../lib/api";
import type { DeepResearchStage, DeepResearchTask } from "../lib/types";

const DEFAULT_TICKER = "NVDA";
const TICKER_PATTERN = /^[A-Z][A-Z0-9.-]{0,9}$/;
const TICKER_IN_QUESTION = /(?:^|[^A-Z0-9.-])([A-Z](?:[A-Z0-9]|[.-](?=[A-Z0-9])){0,9})(?=$|[^A-Z0-9.-])/;
const workflowStages: ReadonlyArray<{ key: DeepResearchStage; label: string }> = [
  { key: "understand_question", label: "理解问题" },
  { key: "detect_significant_price_moves", label: "识别重要波动" },
  { key: "search_news_and_announcements", label: "搜索新闻与公告" },
  { key: "cross_check_evidence", label: "交叉核对证据" },
  { key: "generate_research_report", label: "生成研究报告" },
];

const statusText: Record<DeepResearchTask["status"], string> = {
  queued: "排队中",
  running: "执行中",
  completed: "已完成",
  failed: "失败",
};

function getStageStatus(
  task: DeepResearchTask | null,
  index: number,
): { label: string; className: string } {
  if (!task) return { label: index === 0 ? "入口" : "待执行", className: "" };
  if (task.status === "completed") return { label: "已完成", className: "is-complete" };

  const currentIndex = task.current_stage
    ? workflowStages.findIndex((stage) => stage.key === task.current_stage)
    : -1;
  if (task.status === "queued") return { label: "排队中", className: "" };
  if (currentIndex < 0) {
    return index === 0
      ? { label: task.status === "failed" ? "失败" : "执行中", className: task.status === "failed" ? "is-failed" : "is-active" }
      : { label: "待执行", className: "" };
  }
  if (index < currentIndex) return { label: "已完成", className: "is-complete" };
  if (index === currentIndex) {
    return task.status === "failed"
      ? { label: "失败", className: "is-failed" }
      : { label: "执行中", className: "is-active" };
  }
  return { label: "待执行", className: "" };
}

function normalizeTicker(value: string): string {
  return value.trim().toUpperCase();
}

function extractTicker(value: string): string | null {
  const match = value.match(TICKER_IN_QUESTION);
  return match ? normalizeTicker(match[1]) : null;
}

export function DeepResearchForm({ initialTicker = DEFAULT_TICKER }: { initialTicker?: string }) {
  const [ticker, setTicker] = useState(normalizeTicker(initialTicker) || DEFAULT_TICKER);
  const [question, setQuestion] = useState(
    `研究 ${normalizeTicker(initialTicker) || DEFAULT_TICKER} 最近有哪些重大事项？`,
  );
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
    const extractedTicker = extractTicker(question);
    const normalizedTicker = normalizeTicker(extractedTicker || ticker);
    if (!extractedTicker || !normalizedTicker) {
      setError("请在研究问题中写入美股代码，例如：研究 NVDA 最近有哪些重大事项？");
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
    <>
      <section className="research-dialog stack" role="group" aria-label="深度研究对话框">
      <div className="section-heading">
        <div>
          <span className="eyebrow">研究对话</span>
          <h2>研究 {ticker || "美股"} 的近期情况</h2>
          <p>告诉我你想研究哪家公司，以及最想了解的问题。</p>
        </div>
        <div className="dialog-badges">
          <span className="tag cyan">支持所有美股代码</span>
          <span className="tag amber">异步执行</span>
        </div>
      </div>
        <textarea
          id="deep-question"
          aria-label="研究问题"
          placeholder="例如：研究 NVDA 最近有哪些重大事项？公司的主要业务风险是什么？"
          value={question}
          onChange={(event) => {
            const nextQuestion = event.target.value;
            setQuestion(nextQuestion);
            const nextTicker = extractTicker(nextQuestion);
            if (nextTicker) setTicker(nextTicker);
          }}
          style={{ minHeight: 112 }}
        />
        <div className="dialog-footer">
          <span className="dialog-hint">在同一个问题框中写入标的和问题。</span>
          <div className="form-actions">
            <button className="button" type="button" onClick={submit} disabled={loading}>
              {loading ? "创建任务中…" : "开始深度研究"}
            </button>
            {task && <span className="tag cyan">任务：{statusText[task.status]}</span>}
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
      <section className="card workflow-card" style={{ marginTop: 16 }}>
        <div className="section-heading">
          <div>
            <span className="eyebrow">工作流阶段</span>
            <h2>从问题到报告</h2>
          </div>
          <span className="tag">5 个阶段</span>
        </div>
        <div className="stage-list">
          {workflowStages.map((stage, index) => {
            const stageStatus = getStageStatus(task, index);
            return (
              <div key={stage.key} className={`stage ${stageStatus.className}`}>
                <span className="stage-number">0{index + 1}</span>
                <span>{stage.label}</span>
                <span className="stage-status">{stageStatus.label}</span>
              </div>
            );
          })}
        </div>
      </section>
    </>
  );
}
