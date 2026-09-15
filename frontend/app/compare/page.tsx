import Link from "next/link";

import { getResearch } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function ComparePage() {
  const [nvda, amd] = await Promise.all([getResearch("NVDA"), getResearch("AMD")]);
  const rows = [["Revenue growth", nvda.financial_metrics?.revenue_growth?.value, amd.financial_metrics?.revenue_growth?.value], ["Growth score", nvda.growth_score.final_score, amd.growth_score.final_score], ["Overall score", nvda.overall_score.final_score, amd.overall_score.final_score]] as const;
  return <main className="shell"><header className="topbar"><Link className="brand" href="/">SignalRoom</Link><Link href="/" className="nav">Back home</Link></header><span className="eyebrow">Compare / fundamentals + evidence</span><h1>NVDA <span className="muted">vs</span> AMD.</h1><section className="card"><div className="grid" style={{ marginTop: 0 }}>{rows.map(([label, left, right]) => <div key={label} className="stack"><span className="muted">{label}</span><strong>{String(left ?? "n/a")}</strong><span>{String(right ?? "n/a")}</span></div>)}</div></section></main>;
}
