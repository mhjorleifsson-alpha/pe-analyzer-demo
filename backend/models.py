from typing import Literal
from pydantic import BaseModel


class CompanyVitals(BaseModel):
    name: str | None = None
    industry: str | None = None
    sector: str | None = None
    geography: str | None = None
    founding_year: int | None = None
    description: str | None = None


class DealClassification(BaseModel):
    category: Literal["buyout", "growth", "minority"]
    confidence: float
    reasoning: str


class BuyoutMetrics(BaseModel):
    revenue: str | None = None
    ebitda: str | None = None
    ebitda_margin: str | None = None
    revenue_growth_rate: str | None = None
    net_debt: str | None = None
    leverage_ratio: str | None = None


class GrowthMetrics(BaseModel):
    revenue: str | None = None
    arr: str | None = None
    mrr: str | None = None
    revenue_growth_rate: str | None = None
    gross_margin: str | None = None
    net_revenue_retention: str | None = None
    debt_levels: str | None = None


class MinorityMetrics(BaseModel):
    revenue: str | None = None
    ebitda: str | None = None
    arr: str | None = None
    revenue_growth_rate: str | None = None
    ebitda_margin: str | None = None
    gross_margin: str | None = None
    debt_levels: str | None = None


class DealAnalysis(BaseModel):
    vitals: CompanyVitals
    classification: DealClassification
    metrics: BuyoutMetrics | GrowthMetrics | MinorityMetrics
