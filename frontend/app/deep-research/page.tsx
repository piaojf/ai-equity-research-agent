import Link from "next/link";

import { DeepResearchForm } from "../../components/deep-research-form";

const stages = ["理解问题", "识别重要波动", "搜索新闻与公告", "交叉核对证据", "生成研究报告"];

export default function DeepResearchPage() {
  return <div className="page-shell"><header className="topbar"><span className="breadcrumb">研究工作台 / 深度研究</span><div className="topbar-actions"><span className="tag amber">后台任务</span><Link href="/stock/NVDA" className="button secondary">返回个股</Link></div></header><div className="page-intro"><span className="eyebrow">深度研究 · 多阶段工作流</span><h1>把一个问题，<br /><span className="muted">拆成一条证据链。</span></h1><p className="lead">提交研究问题后，系统会创建后台任务，按阶段收集市场、新闻和监管文件信息。</p></div><DeepResearchForm /><section className="card" style={{ marginTop: 16 }}><div className="section-heading"><div><span className="eyebrow">工作流阶段</span><h2>从问题到报告</h2></div><span className="tag">5 个阶段</span></div><div className="stage-list">{stages.map((stage, index) => <div key={stage} className="stage"><span className="stage-number">0{index + 1}</span><span>{stage}</span><span className="quiet" style={{ marginLeft: "auto", fontSize: 11 }}>{index === 0 ? "入口" : "待执行"}</span></div>)}</div></section></div>;
}
