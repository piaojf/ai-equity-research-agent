import Link from "next/link";

import { getResearch } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function ComparePage() {
  const [nvda, amd] = await Promise.all([getResearch("NVDA"), getResearch("AMD")]);
  const rows = [["收入增长", nvda.financial_metrics?.revenue_growth?.value, amd.financial_metrics?.revenue_growth?.value, true], ["增长评分", nvda.growth_score.final_score, amd.growth_score.final_score, false], ["综合评分", nvda.overall_score.final_score, amd.overall_score.final_score, false]] as const;
  return <div className="page-shell"><header className="topbar"><span className="breadcrumb">研究工作台 / 股票对比</span><Link href="/" className="button secondary">返回总览</Link></header><div className="page-intro"><span className="eyebrow">横向比较 · 基本面与评分</span><h1>NVDA <span className="muted">对比</span> AMD</h1><p className="lead">用同一套确定性评分标准，快速查看两家芯片公司的核心差异。</p></div><section className="card comparison-table"><div className="comparison-row comparison-head"><span>指标</span><span>NVDA</span><span>AMD</span></div>{rows.map(([label, left, right, isPercent]) => <div key={label} className="comparison-row"><span className="muted">{label}</span><strong>{left == null ? "—" : isPercent ? `${(Number(left) * 100).toFixed(1)}%` : left}</strong><strong>{right == null ? "—" : isPercent ? `${(Number(right) * 100).toFixed(1)}%` : right}</strong></div>)}</section><p className="footer-note">评分由确定性引擎计算；数据来源和缺失字段会在个股详情页中展开。</p></div>;
}
