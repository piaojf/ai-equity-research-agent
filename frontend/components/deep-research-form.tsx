"use client";

import { useEffect, useState } from "react";

import { getDeepResearch, submitDeepResearch } from "../lib/api";
import type { DeepResearchTask } from "../lib/types";

const statusText: Record<DeepResearchTask["status"], string> = { queued: "排队中", running: "执行中", completed: "已完成", failed: "失败" };

export function DeepResearchForm() {
  const [question, setQuestion] = useState("为什么 NVDA 最近出现波动？");
  const [task, setTask] = useState<DeepResearchTask | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!task || task.status === "completed" || task.status === "failed") return;
    const timer = window.setInterval(async () => {
      try { setTask(await getDeepResearch(task.task_id)); }
      catch (requestError) { setError(requestError instanceof Error ? requestError.message : "任务状态查询失败。"); }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [task]);

  async function submit() {
    setLoading(true); setError(null);
    try { const accepted = await submitDeepResearch({ ticker: "NVDA", question }); setTask({ task_id: accepted.task_id, status: accepted.status }); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "深度研究提交失败。"); }
    finally { setLoading(false); }
  }

  return <section className="card stack"><div className="section-heading"><div><span className="eyebrow">研究任务</span><h2>研究 NVDA 的近期波动</h2></div><span className="tag amber">异步执行</span></div><label htmlFor="deep-question" className="muted">研究问题</label><textarea id="deep-question" value={question} onChange={(event) => setQuestion(event.target.value)} style={{ minHeight: 120 }} /><div className="form-actions"><button className="button" type="button" onClick={submit} disabled={loading}>{loading ? "创建任务中…" : "开始深度研究"}</button>{task && <span className="tag cyan">任务：{statusText[task.status]}</span>}</div>{error && <div className="error-box"><strong>任务出现问题</strong><p>{error}</p></div>}{task && <div className="signal"><div className="quick-links"><span className="tag">{statusText[task.status]}</span><span className="tag cyan">任务 ID：{task.task_id.slice(0, 8)}…</span></div>{task.report ? <><h2 style={{ marginTop: 18 }}>{task.report.confidence === "high" ? "高可信度" : task.report.confidence === "medium" ? "中等可信度" : "低可信度"}</h2><p style={{ lineHeight: 1.8 }}>{task.report.conclusion}</p><p className="muted">{task.report.evidence.length} 条证据 · {task.report.major_events.length} 个重要事件</p></> : <p className="muted">任务已接受，系统正在轮询后台状态。</p>}</div>}</section>;
}
