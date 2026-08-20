import json
from pathlib import Path

import pandas as pd
import pytest

from src.analytics import aggregate, enrich, kpis, monthly_trend, pareto, validate_sales, yoy_comparison
from src.build_artifacts import build


def sample() -> pd.DataFrame:
    return pd.DataFrame({
        "order_id": ["1", "2", "3"], "order_date": ["2024-01-01", "2024-02-01", "2025-01-01"],
        "region": ["West", "South", "West"], "channel": ["Online", "Retail", "Online"], "segment": ["SMB", "Consumer", "SMB"],
        "category": ["Technology", "Office", "Technology"], "product": ["Laptop Pro", "Ergo Chair", "Laptop Pro"],
        "units": [2, 1, 1], "unit_price": [100, 200, 100], "discount_pct": [.1, .2, .1], "unit_cost": [60, 100, 60],
    })


def test_validation_and_enrichment():
    e = enrich(sample())
    assert e.loc[0, "revenue"] == 180
    assert e.loc[0, "profit"] == 60


def test_kpis_and_margin():
    k = kpis(enrich(sample()))
    assert k.orders == 3
    assert round(k.revenue, 2) == 430
    assert round(k.margin_pct, 2) == 34.88


@pytest.mark.parametrize("mutator, message", [
    (lambda d: d.drop(columns=["region"]), "Missing columns"),
    (lambda d: d.assign(units=0), "units must be greater"),
    (lambda d: d.assign(discount_pct=2), "discount_pct"),
    (lambda d: d.assign(order_date="not-a-date"), "invalid dates"),
    (lambda d: d.assign(order_id="1"), "duplicate orders"),
    (lambda d: d.assign(unit_price="bad"), "must be numeric"),
])
def test_validation_failures(mutator, message):
    with pytest.raises(ValueError, match=message):
        validate_sales(mutator(sample()))


def test_empty_dataset_rejected():
    with pytest.raises(ValueError, match="empty"):
        validate_sales(sample().iloc[0:0])


def test_aggregate_and_pareto():
    df = enrich(sample())
    agg = aggregate(df, "region")
    assert set(agg["region"]) == {"West", "South"}
    p = pareto(df)
    assert p["cumulative_share_pct"].iloc[-1] == pytest.approx(100)


def test_growth_and_yoy():
    monthly = monthly_trend(enrich(sample()))
    assert monthly.loc[monthly["month"] == "2024-02", "mom_revenue_pct"].iloc[0] < 0
    yoy = yoy_comparison(monthly)
    assert "yoy_revenue_pct" in yoy.columns


def test_artifact_reproducibility(tmp_path: Path):
    source = tmp_path / "sales.csv"
    source.write_text(sample().to_csv(index=False), encoding="utf-8")
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    build(source, first)
    build(source, second)
    assert json.loads(first.read_text()) == json.loads(second.read_text())


def test_committed_artifact_matches_source(tmp_path: Path):
    committed = json.loads(Path("public/analytics.json").read_text(encoding="utf-8"))
    regenerated_path = tmp_path / "analytics.json"
    build(Path("data/sales.csv"), regenerated_path)
    assert json.loads(regenerated_path.read_text(encoding="utf-8")) == committed
