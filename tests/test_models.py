from backend.models import (
    CompanyVitals,
    DealClassification,
    BuyoutMetrics,
    GrowthMetrics,
    MinorityMetrics,
    DealAnalysis,
)


def test_vitals_all_optional():
    v = CompanyVitals()
    assert v.name is None
    assert v.description is None


def test_vitals_with_data():
    v = CompanyVitals(name="Acme Corp", geography="Germany", founding_year=2005)
    assert v.name == "Acme Corp"
    assert v.founding_year == 2005


def test_classification():
    c = DealClassification(category="buyout", confidence=0.92, reasoning="High leverage, mature business")
    assert c.category == "buyout"
    assert 0.0 <= c.confidence <= 1.0


def test_buyout_metrics_all_optional():
    m = BuyoutMetrics()
    assert m.revenue is None
    assert m.leverage_ratio is None


def test_growth_metrics():
    m = GrowthMetrics(arr="€5.2M", revenue_growth_rate="85% YoY")
    assert m.arr == "€5.2M"


def test_minority_metrics():
    m = MinorityMetrics(revenue="€20M", ebitda="€4M")
    assert m.ebitda == "€4M"


def test_deal_analysis_buyout():
    analysis = DealAnalysis(
        vitals=CompanyVitals(name="TestCo"),
        classification=DealClassification(category="buyout", confidence=0.9, reasoning="test"),
        metrics=BuyoutMetrics(revenue="€50M"),
    )
    assert analysis.vitals.name == "TestCo"
    assert analysis.classification.category == "buyout"
