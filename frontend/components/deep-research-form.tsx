"use client";

import { useEffect, useState } from "react";

import { getDeepResearch, submitDeepResearch } from "../lib/api";
import type { DeepResearchTask } from "../lib/types";

export function DeepResearchForm() {
  const [question, setQuestion] = useState("Why did NVDA fall recently?");
  const [task, setTask] = useState<DeepResearchTask | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!task || task.status === "completed" || task.status === "failed") return;
    const timer = window.setInterval(async () => {
      try {
        setTask(await getDeepResearch(task.task_id));
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "Polling failed.");
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [task]);

  async function submit() {
    setLoading(true);
    setError(null);
    try {
      const accepted = await submitDeepResearch({ ticker: "NVDA", question });
      setTask({ task_id: accepted.task_id, status: accepted.status });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Deep Research failed.");
    } finally {
      setLoading(false);
    }
  }

  return <section className="card stack"><label htmlFor="deep-question" className="muted">Research question</label><textarea id="deep-question" value={question} onChange={(event) => setQuestion(event.target.value)} style={{ minHeight: 120, padding: 16, border: "1px solid var(--line)", borderRadius: 12 }} /><button className="button" type="button" onClick={submit} disabled={loading}>{loading ? "Queueing..." : "Start research"}</button>{error && <div className="signal"><span className="pill">error</span><p>{error}</p></div>}{task && <div className="signal"><span className="pill">{task.status}</span>{task.report ? <><h2>{task.report.confidence} confidence</h2><p>{task.report.conclusion}</p><p className="muted">{task.report.evidence.length} evidence items · {task.report.major_events.length} major events</p></> : <p className="muted">HTTP 202 accepted. Polling task {task.task_id}.</p>}</div>}</section>;
}
