export type DealCategory = "buyout" | "growth" | "minority";

export interface CompanyVitals {
  name: string | null;
  industry: string | null;
  sector: string | null;
  geography: string | null;
  founding_year: number | null;
  description: string | null;
}

export interface DealClassification {
  category: DealCategory;
  confidence: number;
  reasoning: string;
}

export interface BuyoutMetrics {
  revenue: string | null;
  ebitda: string | null;
  ebitda_margin: string | null;
  revenue_growth_rate: string | null;
  net_debt: string | null;
  leverage_ratio: string | null;
}

export interface GrowthMetrics {
  revenue: string | null;
  arr: string | null;
  mrr: string | null;
  revenue_growth_rate: string | null;
  gross_margin: string | null;
  net_revenue_retention: string | null;
  debt_levels: string | null;
}

export interface MinorityMetrics {
  revenue: string | null;
  ebitda: string | null;
  arr: string | null;
  revenue_growth_rate: string | null;
  ebitda_margin: string | null;
  gross_margin: string | null;
  debt_levels: string | null;
}

export interface DealAnalysis {
  vitals: CompanyVitals;
  classification: DealClassification;
  metrics: BuyoutMetrics | GrowthMetrics | MinorityMetrics;
}
