import json
from pathlib import Path

import pandas as pd
import pytest

from src.analytics import (
    aggregate,
    discount_intelligence,
    enrich,
    kpis,
    mix_shift,
    monthly_trend,
    pareto,
    product_economics,
    validate_sales,
    yoy_comparison,
)
from src.build_artifacts import build


def sample() -> pd.DataFrame:
    return pd.DataFrame({
        "order_id": ["1", "2", "3", "4"],
        "order_date": ["2024-01-01", "2024-02-01", "2025-01-01", "2025-02-01"],
        "region": ["West", "South", "West", "South"],
        "channel": ["Online", "Retail", "Online", "Retail"],
        "segment": ["SMB", "Consumer", "SMB", "Consumer"],
        "category": ["Technology", "Office", "Technology", "Office"],
        "product": ["Laptop Pro", "Ergo Chair", "Laptop Pro", "Ergo Chair"],
        "units": [2, 1, 1, 2],
        "unit_price": [100, 200, 100, 200],
        "discount_pct": [.1, .2, .1, .1],
        "unit_cost": [60, 100, 60, 100],
    })


def test_validation_and_enrichment():
    e = enrich(sample())
    assert e.loc[0, "revenue"] == 180
    assert e.loc[0, "profit"] == 60
    assert e.loc[0, "discount_amount"] == 20
    assert "discount_band" in e.columns


def test_kpis_and_margin():
    k = kpis(enrich(sample()))
    assert k.orders == 4
    assert round(k.revenue, 2) == 810
    assert round(k.margin_pct, 2) == 37.04
    assert k.gross_revenue > k.revenue
    assert k.discount_leakage > 0


@pytest.mark.parametrize("mutator, message", [
    (lambda d: d.drop(columns=["region"]), "Missing columns"),
    (lambda d: d.assign(units=0), "units must be greater"),
    (lambda d: d.assign(discount_pct=2), "discount_pct"),
    (lambda d: d.assign(order_date="not-a-date"), "invalid dates"),
    (lambda d: d.assign(order_id="1"), "duplicate orders"),
    (lambda d: d.assign(unit_price="bad"), "must be numeric"),
    (lambda d: d.assign(unit_price=float("inf")), "non-finite"),
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
    assert "mom_margin_pp" in monthly.columns
    yoy = yoy_comparison(monthly)
    assert "yoy_revenue_pct" in yoy.columns
    assert "yoy_margin_pp" in yoy.columns


def test_product_quadrants_and_discount_intelligence():
    df = enrich(sample())
    products = product_economics(df)
    assert set(products["commercial_quadrant"]).issubset({"Growth Engine", "Revenue Trap", "Margin Specialist", "Long Tail"})
    bands = discount_intelligence(df)
    assert bands["discount_leakage"].sum() == pytest.approx(df["discount_amount"].sum())
    assert bands["revenue"].sum() == pytest.approx(df["revenue"].sum())


def test_mix_shift_is_percentage_point_change():
    df = enrich(sample())
    shift = mix_shift(df, "category")
    assert "mix_shift_pp" in shift.columns
    assert shift["mix_shift_pp"].sum() == pytest.approx(0)


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
