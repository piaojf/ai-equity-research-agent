"use client";

import { useState } from "react";

import { askSec } from "../lib/api";
import type { SECAskResult } from "../lib/types";

export function SecAskForm() {
  const [question, setQuestion] = useState("What are NVIDIA's major business risks?");
  const [result, setResult] = useState<SECAskResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit() {
    setLoading(true);
    setError(null);
    try {
      setResult(await askSec({ ticker: "NVDA", question }));
    } catch (requestError) {
      setResult(null);
      setError(requestError instanceof Error ? requestError.message : "SEC request failed.");
    } finally {
      setLoading(false);
    }
  }

  return <section className="card stack"><label htmlFor="question" className="muted">Question</label><textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} style={{ minHeight: 140, padding: 16, border: "1px solid var(--line)", borderRadius: 12 }} /><button className="button" type="button" onClick={submit} disabled={loading}>{loading ? "Searching..." : "Search indexed evidence"}</button>{error && <div className="signal"><span className="pill">error</span><p>{error}</p></div>}{result && <div className="signal"><span className="pill">confidence: {result.confidence}</span><p>{result.answer}</p>{result.citations.length > 0 ? <div className="stack">{result.citations.map((citation) => <a key={citation.chunk_id} href={citation.source_url} target="_blank" rel="noreferrer"><strong>{citation.filing_type} · {citation.section}</strong><br />{citation.accession_number} · {citation.chunk_id}<br /><span className="muted">{citation.excerpt}</span></a>)}</div> : <p className="muted">Insufficient evidence. No citation is fabricated.</p>}</div>}</section>;
}
