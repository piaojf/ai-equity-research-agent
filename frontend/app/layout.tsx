import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SignalRoom | Equity Research Agent",
  description: "Evidence-first equity research workspace.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
