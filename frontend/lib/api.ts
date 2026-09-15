export type ScoreBreakdown = {
  score_name: string;
  final_score: number;
  components: Array<{ metric: string; normalized_score: number | null; contribution: number; source: string }>;
  confidence: "low" | "medium" | "high";
};

export type StockOverview = {
  ticker: string;
  quote: { price: number; change_percent: number | null; source: string };
  history: { points: Array<{ date: string; close: number }>; source: string };
};

export type ApiResponse<T> = { request_id: string; data: T; errors: unknown[]; generated_at: string };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function getStock(ticker: string): Promise<StockOverview> {
  const response = await fetch(`${API_BASE}/api/stocks/${encodeURIComponent(ticker)}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Stock data is unavailable.");
  const payload = (await response.json()) as ApiResponse<StockOverview>;
  return payload.data;
}
