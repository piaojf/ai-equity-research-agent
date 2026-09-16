import Link from "next/link";

import { getResearch } from "../../lib/api";

export const dynamic = "force-dynamic";

type SearchParamValue = string | string[] | undefined;

type ComparePageProps = {
  searchParams?: Promise<{
    left?: SearchParamValue;
    right?: SearchParamValue;
  }>;
};

function normalizeTicker(value: SearchParamValue, fallback: string): string {
  const candidate = Array.isArray(value) ? value[0] : value;
  const normalized = candidate?.trim().toUpperCase() ?? "";
  return /^[A-Z0-9.-]{1,10}$/.test(normalized) ? normalized : fallback;
}

export default async function ComparePage({ searchParams }: ComparePageProps) {
  const params = searchParams ? await searchParams : {};
  const leftTicker = normalizeTicker(params.left, "NVDA");
  const rightTicker = normalizeTicker(params.right, "AMD");
  const [leftResearch, rightResearch] = await Promise.all([
    getResearch(leftTicker),
    getResearch(rightTicker),
  ]);
  const rows = [
    [
      "收入增长",
      leftResearch.financial_metrics?.revenue_growth?.value,
      rightResearch.financial_metrics?.revenue_growth?.value,
      true,
    ],
    [
      "增长评分",
      leftResearch.growth_score.final_score,
      rightResearch.growth_score.final_score,
      false,
    ],
    [
      "综合评分",
      leftResearch.overall_score.final_score,
      rightResearch.overall_score.final_score,
      false,
    ],
  ] as const;

  return (
    <div className="page-shell">
      <header className="topbar">
        <span className="breadcrumb">研究工作台 / 股票对比</span>
        <Link href="/" className="button secondary">
          返回总览
        </Link>
      </header>

      <div className="page-intro">
        <span className="eyebrow">横向比较 · 基本面与评分</span>
        <h1>
          {leftTicker} <span className="muted">对比</span> {rightTicker}
        </h1>
        <p className="lead">
          输入任意两只股票代码，用同一套确定性评分标准快速查看核心差异。
        </p>
        <form className="compare-form" action="/compare" method="get">
          <label className="compare-field">
            <span>第一家公司</span>
            <input
              className="input"
              name="left"
              defaultValue={leftTicker}
              placeholder="例如 NVDA"
              maxLength={10}
              pattern="[A-Za-z0-9.-]{1,10}"
              required
            />
          </label>
          <label className="compare-field">
            <span>第二家公司</span>
            <input
              className="input"
              name="right"
              defaultValue={rightTicker}
              placeholder="例如 AMD"
              maxLength={10}
              pattern="[A-Za-z0-9.-]{1,10}"
              required
            />
          </label>
          <button className="button" type="submit">
            开始对比
          </button>
        </form>
      </div>

      <section className="card comparison-table">
        <div className="comparison-row comparison-head">
          <span>指标</span>
          <span>{leftTicker}</span>
          <span>{rightTicker}</span>
        </div>
        {rows.map(([label, left, right, isPercent]) => (
          <div key={label} className="comparison-row">
            <span className="muted">{label}</span>
            <strong>
              {left == null
                ? "—"
                : isPercent
                  ? `${(Number(left) * 100).toFixed(1)}%`
                  : left}
            </strong>
            <strong>
              {right == null
                ? "—"
                : isPercent
                  ? `${(Number(right) * 100).toFixed(1)}%`
                  : right}
            </strong>
          </div>
        ))}
      </section>
      <p className="footer-note">
        评分由确定性引擎计算；数据来源和缺失字段会在个股详情页中展开。
      </p>
    </div>
  );
}
