"use client";

import { useState } from "react";

import { askSec } from "../lib/api";
import type { SECAskResult } from "../lib/types";

const DEFAULT_TICKER = "NVDA";
const TICKER_PATTERN = /^[A-Z][A-Z0-9.-]{0,9}$/;

function normalizeTicker(value: string): string {
  return value.trim().toUpperCase();
}

export function SecAskForm({ initialTicker = DEFAULT_TICKER }: { initialTicker?: string }) {
  const [ticker, setTicker] = useState(normalizeTicker(initialTicker) || DEFAULT_TICKER);
  const [question, setQuestion] = useState("英伟达面临的主要业务风险是什么？");
  const [result, setResult] = useState<SECAskResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit() {
    setLoading(true);
    setError(null);
    const normalizedTicker = normalizeTicker(ticker);
    if (!TICKER_PATTERN.test(normalizedTicker)) {
      setError("请输入有效的美股代码，例如 NVDA、INTC 或 BRK.B。");
      setLoading(false);
      return;
    }
    if (!question.trim()) {
      setError("请输入要检索的问题。");
      setLoading(false);
      return;
    }
    try { setResult(await askSec({ ticker: normalizedTicker, question: question.trim() })); }
    catch (requestError) { setResult(null); setError(requestError instanceof Error ? requestError.message : "SEC 文件检索失败。"); }
    finally { setLoading(false); }
  }

  return <section className="score-layout"><div className="card stack"><div className="section-heading"><div><span className="eyebrow">提问</span><h2>关于 {ticker || "美股"} 的监管文件</h2></div><span className="tag cyan">已索引</span></div><label htmlFor="sec-ticker" className="muted">研究标的</label><input id="sec-ticker" className="input" aria-label="研究标的" value={ticker} onChange={(event) => setTicker(event.target.value)} maxLength={10} autoCapitalize="characters" spellCheck={false} /><label htmlFor="question" className="muted">你的问题</label><textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} style={{ minHeight: 160 }} /><div className="form-actions"><button className="button" type="button" onClick={submit} disabled={loading}>{loading ? "检索中…" : "检索引用证据"}</button><span className="footer-note" style={{ margin: 0 }}>默认检索最新可用 SEC 文件</span></div>{error && <div className="error-box"><strong>请求未完成</strong><p>{error}</p></div>}</div><div className="card"><span className="eyebrow">回答与引用</span>{result ? <><div className="quick-links"><span className="tag">可信度：{result.confidence === "high" ? "高" : result.confidence === "medium" ? "中" : "低"}</span><span className="tag cyan">{result.citations.length} 条引用</span></div><p style={{ lineHeight: 1.8 }}>{result.answer}</p>{result.citations.length > 0 ? <div className="citation-list">{result.citations.map((citation) => <a className="citation" key={citation.chunk_id} href={citation.source_url} target="_blank" rel="noreferrer"><div className="citation-title">{citation.filing_type} · {citation.section}</div><div className="citation-meta">{citation.filing_date} · {citation.accession_number} · {citation.chunk_id}</div><div className="citation-excerpt">{citation.excerpt}</div></a>)}</div> : <div className="empty-state">证据不足，系统不会伪造引用。</div>}</> : <div className="empty-state" style={{ marginTop: 20 }}>提交问题后，回答和 SEC 原文引用会显示在这里。</div>}</div></section>;
}
