import Link from "next/link";

import { DeepResearchForm } from "../../components/deep-research-form";

const stages = ["Understand question", "Detect significant moves", "Search news + announcements", "Cross-check evidence", "Generate report"];

export default function DeepResearchPage() {
  return <main className="shell"><header className="topbar"><Link className="brand" href="/">SignalRoom</Link><span className="pill">worker-ready</span></header><span className="eyebrow">Deep Research / background workflow</span><h1>Why did NVDA fall recently?</h1><DeepResearchForm /><section className="card" style={{ marginTop: 16 }}><div className="stack">{stages.map((stage, index) => <div key={stage} style={{ display: "flex", gap: 14, alignItems: "center" }}><span className="pill">0{index + 1}</span><span>{stage}</span></div>)}</div></section></main>;
}
