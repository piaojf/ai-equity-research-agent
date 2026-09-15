import type { Metadata } from "next";

import { AppShell } from "../components/app-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "SignalRoom｜AI 股票研究工作台",
  description: "以数据、证据和可解释评分为核心的 AI 股票研究工作台。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body><AppShell>{children}</AppShell></body>
    </html>
  );
}
