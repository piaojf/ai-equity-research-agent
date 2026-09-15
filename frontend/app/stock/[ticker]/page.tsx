import Link from "next/link";

import { getResearch, getStock } from "../../../lib/api";

export const dynamic = "force-dynamic";

export default async function StockPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  const symbol = ticker.toUpperCase();
  const [stock, research] = await Promise.all([
    getStock(symbol),
    getResearch(symbol),
  ]);
  const metrics = research.financial_metrics;
  return <main className="shell"><header className="topbar"><Link className="brand" href="/">SignalRoom</Link><Link className="button alt" href="/compare">Compare</Link></header><span className="eyebrow">Stock detail / {symbol}</span><h1>{symbol}<br /><span className="muted">a complete view.</span></h1><div className="grid"><section className="card"><div className="muted">Current price</div><div className="metric"><strong>${stock.quote.price.toFixed(2)}</strong><span className="pill">{stock.quote.change_percent?.toFixed(2) ?? "n/a"}%</span></div><p className="muted">{stock.quote.source} · {stock.quote.is_delayed ? "delayed" : "real-time"} · volume {stock.quote.volume?.toLocaleString() ?? "n/a"}</p><p className="muted">{stock.history.points.length} historical sessions through {stock.history.as_of.slice(0, 10)}.</p></section><section className="card"><span className="eyebrow">Score breakdown</span><h2>Why {research.overall_score.final_score}?</h2><div className="stack"><span>Fundamental: {research.fundamental_score.final_score}</span><span>Growth: {research.growth_score.final_score}</span><span>Valuation: {research.valuation_score.final_score}</span><span>Risk quality: {research.risk_score.final_score}</span></div><Link className="button" href="/sec-ask">Ask SEC filings</Link></section><section className="card"><span className="eyebrow">Financial metrics</span><h2>{metrics ? "Source-attributed" : "Unavailable"}</h2><div className="stack"><span>Revenue: {metrics?.revenue?.value?.toLocaleString() ?? "n/a"}</span><span>Revenue growth: {metrics?.revenue_growth?.value?.toLocaleString() ?? "n/a"}</span><span>EPS: {metrics?.eps?.value?.toLocaleString() ?? "n/a"}</span><span>FCF: {metrics?.free_cash_flow?.value?.toLocaleString() ?? "n/a"}</span></div></section><section className="card"><span className="eyebrow">AI research summary</span><h2>{research.confidence} confidence</h2><p className="muted">{research.summary}</p><h3>Catalysts</h3><p className="muted">{research.catalysts.join(" · ")}</p><h3>Risks</h3><p className="muted">{research.risks.join(" · ")}</p><Link className="button" href="/deep-research">Start deep research</Link></section></div></main>;
}
