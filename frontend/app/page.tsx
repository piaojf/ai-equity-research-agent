import Link from "next/link";

import { TickerSearch } from "../components/ticker-search";

const tickers = ["NVDA", "AAPL", "MSFT", "TSLA", "AMD"];

export default function HomePage() {
  return <div className="page-shell">
    <header className="topbar"><span className="breadcrumb">研究工作台 / 总览</span><div className="topbar-actions"><span className="tag cyan">数据优先</span><span className="tag">实时接口</span></div></header>
    <section className="hero">
      <div className="hero-copy"><span className="eyebrow">证据驱动的股票研究</span><h1>让每一个结论，<br /><span className="muted">都能找到依据。</span></h1><p className="lead">SignalRoom 将市场行情、SEC 财务数据、可解释评分和 AI 研究串成一条清晰的证据链。</p><TickerSearch /><div className="quick-links">{tickers.map((ticker) => <Link key={ticker} href={`/stock/${ticker}`} className="pill">查看 {ticker}</Link>)}</div></div>
      <div className="hero-visual"><span className="eyebrow">今日研究摘要</span><div className="metric"><div><div className="muted">综合评分</div><strong>82</strong></div><span className="tag">高可信度</span></div><p className="muted">每项评分都会保留原始值、归一化分数、权重、贡献度与数据来源。</p><div className="data-row" style={{ marginTop: 28 }}><span>研究状态</span><strong style={{ color: "var(--signal)" }}>数据链路正常</strong></div></div>
    </section>
    <section className="feature-grid"><article className="card feature-card"><span className="feature-number">01 / 评分引擎</span><h2>数字可解释</h2><p>增长、估值、基本面和风险由 Python 确定性计算，LLM 不直接编造核心数字。</p></article><article className="card feature-card"><span className="feature-number">02 / 证据链</span><h2>来源可追溯</h2><p>SEC 文件切片保留备案编号、章节、文本分片编号和原文链接，方便复核。</p></article><article className="card feature-card"><span className="feature-number">03 / 智能体工作流</span><h2>研究可拆解</h2><p>复杂问题进入后台任务，分阶段收集行情、新闻、公告和监管文件证据。</p></article></section>
  </div>;
}
