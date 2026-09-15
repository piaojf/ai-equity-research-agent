import Link from "next/link";

export default function ComparePage() {
  const rows = [["Revenue growth", "+20.0%", "+12.4%"], ["P/E", "24.0", "31.2"], ["Growth score", "88", "76"], ["Overall score", "82", "74"]];
  return <main className="shell"><header className="topbar"><Link className="brand" href="/">SignalRoom</Link><Link href="/" className="nav">Back home</Link></header><span className="eyebrow">Compare / fundamentals + evidence</span><h1>NVDA <span className="muted">vs</span> AMD.</h1><section className="card"><div className="grid" style={{ marginTop: 0 }}>{rows.map(([label, left, right]) => <div key={label} className="stack"><span className="muted">{label}</span><strong>{left}</strong><span>{right}</span></div>)}</div></section></main>;
}
