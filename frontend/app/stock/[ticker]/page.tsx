import Link from "next/link";

export default async function StockPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  const symbol = ticker.toUpperCase();
  return <main className="shell"><header className="topbar"><Link className="brand" href="/">SignalRoom</Link><Link className="button alt" href="/compare">Compare</Link></header><span className="eyebrow">Stock detail / {symbol}</span><h1>{symbol}<br /><span className="muted">a complete view.</span></h1><div className="grid"><section className="card"><div className="muted">Current price</div><div className="metric"><strong>$182.00</strong><span className="pill">+1.11%</span></div><p className="muted">Mock mode is active. Connect the backend to load source-attributed market history.</p></section><section className="card"><span className="eyebrow">Score breakdown</span><h2>Why 82?</h2><p className="muted">Revenue growth 40% · EPS growth 30% · FCF growth 30%. Each contribution is preserved in the API response.</p><Link className="button" href="/sec-ask">Ask SEC filings</Link></section><section className="card"><span className="eyebrow">Research state</span><h2>Ready to investigate.</h2><p className="muted">Launch a background research task to correlate price moves with evidence.</p><Link className="button" href="/deep-research">Start deep research</Link></section></div></main>;
}
