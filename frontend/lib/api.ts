import type {
  ApiResponse,
  DeepResearchTask,
  EquityResearchReport,
  SECAskRequest,
  SECAskResult,
  StockOverview,
} from "./types";

const publicApiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const serverApiBase = process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8000";

function apiUrl(path: string): string {
  if (typeof window === "undefined") {
    return `${serverApiBase.replace(/\/$/, "")}${path}`;
  }
  return `${publicApiBase.replace(/\/$/, "")}${path}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), { ...init, cache: "no-store" });
  const payload = (await response.json()) as ApiResponse<T>;
  if (!response.ok) {
    throw new Error(payload.errors?.[0]?.message ?? "API request failed.");
  }
  return payload.data;
}

export function getStock(ticker: string): Promise<StockOverview> {
  return request<StockOverview>(`/api/stocks/${encodeURIComponent(ticker)}`);
}

export function getResearch(ticker: string): Promise<EquityResearchReport> {
  return request<EquityResearchReport>(`/api/research/${encodeURIComponent(ticker)}`);
}

export function askSec(input: SECAskRequest): Promise<SECAskResult> {
  return request<SECAskResult>("/api/sec/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function submitDeepResearch(input: {
  ticker: string;
  question: string;
}): Promise<{ task_id: string; status: "queued" }> {
  return request<{ task_id: string; status: "queued" }>("/api/deep-research", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function getDeepResearch(taskId: string): Promise<DeepResearchTask> {
  return request<DeepResearchTask>(`/api/deep-research/${taskId}`);
}
