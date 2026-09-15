"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const nav = [
  { href: "/", label: "总览", icon: "⌂" },
  { href: "/compare", label: "股票对比", icon: "⇄" },
  { href: "/sec-ask", label: "SEC 研报问答", icon: "§" },
  { href: "/deep-research", label: "深度研究", icon: "◌" },
];

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  return <div className="app-frame">
    <aside className="sidebar">
      <Link href="/" className="brand-mark">
        <span className="brand-symbol" aria-hidden="true"><span className="logo-orbit" /><span className="logo-core" /></span>
        <span><span className="brand-name">SignalRoom</span><span className="brand-caption">AI 股票研究工作台</span></span>
      </Link>
      <span className="local-badge">本机演示环境 · v0.1</span>
      <nav className="side-nav" aria-label="主导航">
        {nav.map((item) => { const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href); return <Link key={item.href} href={item.href} className={`side-link ${active ? "active" : ""}`}><span className="side-icon">{item.icon}</span>{item.label}</Link>; })}
      </nav>
      <div className="side-note">
        <span className="eyebrow">研究原则</span>
        <p>行情、基本面、证据和研究叙事彼此分层，核心评分由确定性引擎计算。</p>
        <div className="side-status"><span className="status-dot" />数据接口已连接</div>
      </div>
      <p className="side-footer">SignalRoom / 作品集构建<br />仅用于研究与教育演示</p>
    </aside>
    <main className="app-main">{children}</main>
  </div>;
}
