import Link from "next/link";

export default function SecAskPage() {
  return <main className="shell"><header className="topbar"><Link className="brand" href="/">SignalRoom</Link><Link href="/stock/NVDA" className="nav">Back to stock</Link></header><span className="eyebrow">SEC Ask / citation-aware</span><h1>Ask the filing.</h1><section className="card stack"><label htmlFor="question" className="muted">Question</label><textarea id="question" defaultValue="What are NVIDIA's major business risks?" style={{ minHeight: 140, padding: 16, border: "1px solid var(--line)", borderRadius: 12 }} /><button className="button" type="button">Search indexed evidence</button><div className="signal"><span className="pill">confidence: low</span><p className="muted">Available filings do not provide sufficient evidence. Answers will show accession number, section, chunk ID and excerpt when evidence is indexed.</p></div></section></main>;
}
