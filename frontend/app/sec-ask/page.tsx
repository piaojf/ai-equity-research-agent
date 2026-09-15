import Link from "next/link";

import { SecAskForm } from "../../components/sec-ask-form";

export default function SecAskPage() {
  return <main className="shell"><header className="topbar"><Link className="brand" href="/">SignalRoom</Link><Link href="/stock/NVDA" className="nav">Back to stock</Link></header><span className="eyebrow">SEC Ask / citation-aware</span><h1>Ask the filing.</h1><SecAskForm /></main>;
}
