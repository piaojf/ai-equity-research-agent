import Link from "next/link";

import { SecAskForm } from "../../components/sec-ask-form";

function normalizeTicker(value: string | undefined): string {
  const ticker = (value ?? "").trim().toUpperCase();
  return /^[A-Z][A-Z0-9.-]{0,9}$/.test(ticker) ? ticker : "NVDA";
}

export default async function SecAskPage({ searchParams }: { searchParams: Promise<{ ticker?: string | string[] }> }) {
  const params = await searchParams;
  const rawTicker = Array.isArray(params.ticker) ? params.ticker[0] : params.ticker;
  const ticker = normalizeTicker(rawTicker);
  return <div className="page-shell"><header className="topbar"><span className="breadcrumb">研究工作台 / SEC 研报问答</span><Link href={`/stock/${encodeURIComponent(ticker)}`} className="button secondary">返回 {ticker}</Link></header><div className="page-intro"><span className="eyebrow">SEC 问答 · 引用感知</span><h1>直接问原文。</h1><p className="lead">向 SEC 文件提问。每个回答都必须带有可打开的备案文件引用，不生成虚构证据。</p></div><SecAskForm initialTicker={ticker} /></div>;
}
