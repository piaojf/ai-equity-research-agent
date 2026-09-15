"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function TickerSearch() {
  const [ticker, setTicker] = useState("");
  const router = useRouter();

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const symbol = ticker.trim().toUpperCase();
    if (symbol) router.push(`/stock/${encodeURIComponent(symbol)}`);
  }

  return <form className="search" onSubmit={submit}><input aria-label="Ticker" placeholder="Search ticker, e.g. NVDA" value={ticker} onChange={(event) => setTicker(event.target.value)} /><button className="button" type="submit">Search</button></form>;
}
