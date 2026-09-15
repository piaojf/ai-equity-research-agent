"use client";

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main className="page-shell"><div className="error-box"><span className="eyebrow">应用错误</span><h1 style={{ fontSize: 42 }}>研究工作台遇到异常状态。</h1><p>已有研究数据不会丢失，请重新加载当前页面。</p><button className="button" onClick={() => reset()}>重新加载</button></div></main>;
}
