"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const nav = [
  { href: "/", label: "Overview", icon: "⌂" },
  { href: "/compare", label: "Compare", icon: "⇄" },
  { href: "/sec-ask", label: "SEC Ask", icon: "§" },
  { href: "/deep-research", label: "Deep Research", icon: "◌" },
];

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  return <div className="min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
    <aside className="border-b border-white/[.08] bg-ink/70 px-5 py-5 lg:sticky lg:top-0 lg:h-screen lg:border-b-0 lg:border-r">
      <div className="flex items-center justify-between lg:block">
        <Link href="/" className="group inline-flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-signal font-mono text-lg font-black text-ink">S</span>
          <span><span className="block text-sm font-bold tracking-wide">Signal Room</span><span className="block font-mono text-[9px] uppercase tracking-[.2em] text-quiet">Equity intelligence</span></span>
        </Link>
        <span className="rounded-full border border-signal/25 bg-signal/10 px-2 py-1 font-mono text-[9px] uppercase tracking-widest text-signal lg:mt-10 lg:inline-block">Mock mode</span>
      </div>
      <nav className="mt-7 flex gap-2 overflow-x-auto lg:block lg:space-y-1" aria-label="Primary navigation">
        {nav.map((item) => { const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href); return <Link key={item.href} href={item.href} className={`flex min-w-max items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition lg:w-full ${active ? "bg-white/[.09] text-signal" : "text-quiet hover:bg-white/[.05] hover:text-white"}`}><span className="w-5 text-center font-mono text-base">{item.icon}</span>{item.label}</Link>; })}
      </nav>
      <div className="mt-8 hidden rounded-xl border border-white/[.07] bg-panel/70 p-4 lg:block">
        <p className="eyebrow">Research posture</p><p className="mt-3 text-sm leading-6 text-white/80">Data, score, evidence, research. Narrative never changes the deterministic score.</p>
        <div className="mt-4 flex items-center gap-2 text-[11px] text-quiet"><span className="h-2 w-2 rounded-full bg-signal" /> Providers are explicit</div>
      </div>
      <p className="mt-8 hidden font-mono text-[10px] leading-5 text-quiet/60 lg:block">v0.1 · portfolio build<br />Educational use only</p>
    </aside>
    <main className="min-w-0">{children}</main>
  </div>;
}
