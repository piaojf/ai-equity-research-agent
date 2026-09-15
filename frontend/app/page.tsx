import Link from "next/link";

import { TickerSearch } from "../components/ticker-search";

const tickers = ["NVDA", "AAPL", "MSFT", "TSLA", "AMD"];

export default function HomePage() {
  return (
    <main className="shell">
      <header className="topbar"><Link className="brand" href="/">SignalRoom</Link><nav className="nav"><Link href="/stock/NVDA">Dashboard</Link><Link href="/compare">Compare</Link><Link href="/deep-research">Deep Research</Link></nav></header>
      <section className="hero">
        <div><span className="eyebrow">Evidence-first equity intelligence</span><h1>Research that shows its work.</h1><p className="lead">A production-style workspace for market signals, deterministic scoring, SEC evidence and explainable AI research.</p><div className="stack" style={{ marginTop: 28 }}><TickerSearch /><Link className="button" href="/stock/NVDA">Explore NVDA</Link><div className="nav">{tickers.map((ticker) => <Link key={ticker} href={`/stock/${ticker}`} className="pill">{ticker}</Link>)}</div></div></div>
        <div className="signal"><span className="eyebrow">Today&apos;s research brief</span><div className="metric"><div><div className="muted">Overall score</div><strong>82</strong></div><span className="pill">high confidence</span></div><p className="muted">Every score component keeps its raw value, weight, contribution and source.</p></div>
      </section>
      <section className="grid"><article className="card"><span className="eyebrow">01 / Scores</span><h2>Deterministic core</h2><p className="muted">Growth, valuation, fundamentals and risk stay in Python. No LLM invented numbers.</p></article><article className="card"><span className="eyebrow">02 / Evidence</span><h2>Traceable claims</h2><p className="muted">SEC filing chunks become citations with accession numbers and stable chunk IDs.</p></article><article className="card"><span className="eyebrow">03 / Agents</span><h2>Deep research</h2><p className="muted">Long-running questions become background tasks with stages, events and evidence.</p></article></section>
    </main>
  );
}
