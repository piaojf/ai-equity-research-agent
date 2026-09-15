export type DataMode = "mock" | "real" | "hybrid";
export type Confidence = "low" | "medium" | "high";

export interface ApiErrorItem { code: string; message: string; retryable?: boolean; details?: Record<string, unknown>; }
export interface ApiResponse<T> { request_id: string; data: T; errors: ApiErrorItem[]; generated_at: string; }

export interface PriceSnapshot { ticker: string; price: number; previous_close: number; change: number; change_percent: number; open?: number; high?: number; low?: number; volume?: number; currency: string; as_of: string; retrieved_at: string; source: string; source_url?: string; is_delayed: boolean; }
export interface HistoricalPricePoint { date: string; open: number; high: number; low: number; close: number; volume: number; }
export interface StockOverview { ticker: string; quote: PriceSnapshot; history: { ticker: string; period: string; points: HistoricalPricePoint[]; source: string; as_of: string; retrieved_at: string; is_delayed: boolean; }; }

export interface MetricValue { value: number | null; source: string; source_url?: string; as_of?: string; retrieved_at: string; }
export interface FinancialMetrics { ticker: string; currency?: string; revenue?: MetricValue; revenue_growth?: MetricValue; eps?: MetricValue; eps_growth?: MetricValue; gross_margin?: MetricValue; operating_margin?: MetricValue; net_income?: MetricValue; free_cash_flow?: MetricValue; fcf_growth?: MetricValue; pe?: MetricValue; forward_pe?: MetricValue; peg?: MetricValue; limitations: string[]; }
export interface ScoreComponent { metric: string; raw_value: number | null; normalized_score: number | null; weight: number; contribution: number; source: string; source_url?: string; }
export interface ScoreBreakdown { score_name: string; final_score: number; components: ScoreComponent[]; methodology_version: string; missing_metrics: string[]; limitations: string[]; confidence: Confidence; }
export interface NewsItem { headline: string; source: string; published_at?: string; source_url?: string; }
export interface NewsAnalysis { status: "available" | "not_configured" | "unavailable"; articles: NewsItem[]; summary: string; limitations: string[]; }
export interface Citation { ticker: string; filing_type: string; filing_date: string; accession_number: string; section: string; chunk_id: string; source_url: string; excerpt: string; page_or_anchor?: string; }
export interface SecResearchResult { status: "available" | "not_configured" | "unavailable"; summary: string; citations: Citation[]; limitations: string[]; }
export interface EquityResearchReport { ticker: string; generated_at: string; summary: string; fundamental_score: ScoreBreakdown; growth_score: ScoreBreakdown; valuation_score: ScoreBreakdown; risk_score: ScoreBreakdown; sentiment_score?: ScoreBreakdown; fundamental_view: string; valuation_view: string; sentiment: string; thesis: string[]; risks: string[]; catalysts: string[]; scores: Record<string, ScoreBreakdown>; overall_score: ScoreBreakdown; market_data?: StockOverview; financial_metrics?: FinancialMetrics; news: NewsAnalysis; sec_research?: SecResearchResult; key_metrics: Record<string, number | null>; data_sources: string[]; confidence: Confidence; errors: string[]; limitations: string[]; }
export interface ResearchInput { ticker: string; question?: string; include_sec_research?: boolean; }
export interface Evidence { id: string; source: string; title: string; url: string; published_at?: string; summary: string; evidence_type: "market" | "news" | "filing" | "announcement"; }
export interface MajorEvent { date: string; title: string; price_change?: number; evidence_ids: string[]; }
export interface DeepResearchTask { task_id: string; request_id: string; ticker: string; question: string; status: "queued" | "running" | "completed" | "failed"; current_stage: string; major_events: MajorEvent[]; evidence: Evidence[]; conclusion?: string; confidence: Confidence; limitations: string[]; error?: string; }
export interface SECAskRequest { ticker: string; question: string; filing_type?: string; limit?: number; }
export interface SECAskResult { ticker: string; question: string; answer: string; citations: Citation[]; confidence: Confidence; limitations: string[]; }
