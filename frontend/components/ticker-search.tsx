"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { searchStocks } from "../lib/api";
import type { StockSearchItem } from "../lib/types";

export function TickerSearch() {
  const [ticker, setTicker] = useState("");
  const [suggestions, setSuggestions] = useState<StockSearchItem[]>([]);
  const [searching, setSearching] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const query = ticker.trim();
    if (!query) {
      setSuggestions([]);
      setSearching(false);
      return;
    }

    let active = true;
    setSearching(true);
    const timer = window.setTimeout(() => {
      searchStocks(query)
        .then((items) => {
          if (active) setSuggestions(items);
        })
        .catch(() => {
          if (active) setSuggestions([]);
        })
        .finally(() => {
          if (active) setSearching(false);
        });
    }, 250);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [ticker]);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const symbol = ticker.trim().toUpperCase();
    if (symbol) router.push(`/stock/${encodeURIComponent(symbol)}`);
  }

  return (
    <div className="ticker-search">
      <form className="search" onSubmit={submit}>
        <input
          aria-autocomplete="list"
          aria-controls="stock-suggestions"
          aria-label="股票代码或公司名称"
          autoComplete="off"
          placeholder="输入股票代码或公司名称，例如 NVDA"
          role="combobox"
          value={ticker}
          onChange={(event) => setTicker(event.target.value)}
        />
        <button className="button" type="submit">
          开始研究
        </button>
      </form>
      {(searching || suggestions.length > 0) && (
        <div className="autocomplete-menu" id="stock-suggestions" role="listbox">
          {searching && <div className="autocomplete-status">正在搜索股票目录…</div>}
          {!searching && suggestions.map((item) => (
            <button
              className="autocomplete-option"
              key={item.ticker}
              onClick={() => router.push(`/stock/${encodeURIComponent(item.ticker)}`)}
              role="option"
              type="button"
            >
              <strong>{item.ticker}</strong>
              <span>{item.company_name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
