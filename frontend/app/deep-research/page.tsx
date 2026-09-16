import Link from "next/link";

import { DeepResearchForm } from "../../components/deep-research-form";

function normalizeTicker(value: unknown): string {
  if (typeof value !== "string") return "NVDA";
  const ticker = value.trim().toUpperCase();
  return /^[A-Z][A-Z0-9.-]{0,9}$/.test(ticker) ? ticker : "NVDA";
}

export default async function DeepResearchPage({
  searchParams,
}: {
  searchParams: Promise<{ ticker?: string | string[] }>;
}) {
  const params = await searchParams;
  const ticker = normalizeTicker(Array.isArray(params.ticker) ? params.ticker[0] : params.ticker);

  return <div className="page-shell"><header className="topbar"><span className="breadcrumb">研究工作台 / 深度研究</span><div className="topbar-actions"><span className="tag amber">后台任务</span><Link href={`/stock/${encodeURIComponent(ticker)}`} className="button secondary">返回个股</Link></div></header><div className="page-intro"><span className="eyebrow">深度研究 · 多阶段工作流</span><h1>把一个问题，<br /><span className="muted">拆成一条证据链。</span></h1><p className="lead">提交研究问题后，系统会创建后台任务，按阶段收集市场、新闻和监管文件信息。</p></div><DeepResearchForm initialTicker={ticker} /></div>;
}
