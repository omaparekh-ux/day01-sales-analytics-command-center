"""Validated, reproducible sales analytics domain logic."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

import numpy as np
import pandas as pd

REQUIRED_COLUMNS: Final[set[str]] = {
    "order_id", "order_date", "region", "channel", "segment", "category",
    "product", "units", "unit_price", "discount_pct", "unit_cost",
}
TEXT_COLUMNS: Final[tuple[str, ...]] = (
    "order_id", "region", "channel", "segment", "category", "product"
)
NUMERIC_COLUMNS: Final[tuple[str, ...]] = (
    "units", "unit_price", "discount_pct", "unit_cost"
)
SAFE_DIMENSIONS: Final[tuple[str, ...]] = ("category", "region", "channel", "segment", "product")


@dataclass(frozen=True)
class KPI:
    revenue: float
    profit: float
    margin_pct: float
    orders: int
    units: int
    aov: float
    avg_discount_pct: float
    gross_revenue: float
    discount_leakage: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def load_sales(path: str) -> pd.DataFrame:
    """Load sales CSV as strings first so validation controls coercion."""
    return pd.read_csv(path)


def validate_sales(df: pd.DataFrame) -> None:
    """Fail fast on schema, nulls, types, duplicates and commercial rules."""
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("Sales dataset is empty")
    if df[list(TEXT_COLUMNS)].isna().any().any():
        raise ValueError("Text dimensions contain null values")
    if df["order_date"].isna().any():
        raise ValueError("order_date contains null values")
    parsed_dates = pd.to_datetime(df["order_date"], utc=True, errors="coerce", format="mixed")
    if parsed_dates.isna().any():
        raise ValueError("order_date contains invalid dates")
    if df["order_id"].duplicated().any():
        raise ValueError("order_id must be unique; duplicate orders detected")
    for column in NUMERIC_COLUMNS:
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise ValueError(f"{column} must be numeric")
        if df[column].isna().any():
            raise ValueError(f"{column} contains null values")
        if not np.isfinite(df[column].to_numpy(dtype=float)).all():
            raise ValueError(f"{column} contains non-finite values")
    if (df["units"] <= 0).any():
        raise ValueError("units must be greater than zero")
    if (df["unit_price"] <= 0).any():
        raise ValueError("unit_price must be greater than zero")
    if (df["unit_cost"] < 0).any():
        raise ValueError("unit_cost cannot be negative")
    if not df["discount_pct"].between(0, 1, inclusive="both").all():
        raise ValueError("discount_pct must be between 0 and 1")
    if (df["unit_cost"] > df["unit_price"]).any():
        raise ValueError("unit_cost cannot exceed unit_price before discount")


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Create transaction economics and calendar dimensions."""
    validate_sales(df)
    out = df.copy()
    out["order_date"] = pd.to_datetime(out["order_date"], utc=True)
    out["gross_revenue"] = out["units"] * out["unit_price"]
    out["discount_amount"] = out["gross_revenue"] * out["discount_pct"]
    out["revenue"] = out["gross_revenue"] - out["discount_amount"]
    out["cost"] = out["units"] * out["unit_cost"]
    out["profit"] = out["revenue"] - out["cost"]
    out["margin_pct"] = np.where(out["revenue"] > 0, out["profit"] / out["revenue"] * 100, 0.0)
    out["realized_unit_price"] = np.where(out["units"] > 0, out["revenue"] / out["units"], 0.0)
    out["month"] = out["order_date"].dt.strftime("%Y-%m")
    out["year"] = out["order_date"].dt.year
    out["quarter"] = out["order_date"].dt.tz_localize(None).dt.to_period("Q").astype(str)
    out["weekday"] = out["order_date"].dt.day_name()
    out["discount_band"] = pd.cut(
        out["discount_pct"],
        bins=[-0.001, 0.05, 0.10, 0.15, 0.20, 1.0],
        labels=["0–5%", "5–10%", "10–15%", "15–20%", "20%+"],
    ).astype(str)
    return out


def kpis(df: pd.DataFrame) -> KPI:
    """Calculate executive KPIs for a validated/enriched frame."""
    revenue = float(df["revenue"].sum())
    profit = float(df["profit"].sum())
    gross_revenue = float(df["gross_revenue"].sum())
    discount_leakage = gross_revenue - revenue
    orders = int(df["order_id"].nunique())
    return KPI(
        revenue=revenue,
        profit=profit,
        margin_pct=(profit / revenue * 100) if revenue else 0.0,
        orders=orders,
        units=int(df["units"].sum()),
        aov=(revenue / orders) if orders else 0.0,
        avg_discount_pct=float(df["discount_pct"].mean() * 100) if len(df) else 0.0,
        gross_revenue=gross_revenue,
        discount_leakage=discount_leakage,
    )


def aggregate(df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Aggregate commercial performance by a safe business dimension."""
    if dimension not in SAFE_DIMENSIONS:
        raise ValueError(f"Unsupported dimension: {dimension}")
    out = (
        df.groupby(dimension, as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            profit=("profit", "sum"),
            orders=("order_id", "nunique"),
            units=("units", "sum"),
            gross_revenue=("gross_revenue", "sum"),
            discount_amount=("discount_amount", "sum"),
            avg_discount_pct=("discount_pct", "mean"),
        )
    )
    out["margin_pct"] = np.where(out["revenue"] > 0, out["profit"] / out["revenue"] * 100, 0.0)
    out["discount_leakage"] = out["gross_revenue"] - out["revenue"]
    out["revenue_per_unit"] = np.where(out["units"] > 0, out["revenue"] / out["units"], 0.0)
    return out.sort_values("revenue", ascending=False).reset_index(drop=True)


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Return monthly revenue, profit, margin and discount economics."""
    monthly = (
        df.groupby("month", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            profit=("profit", "sum"),
            orders=("order_id", "nunique"),
            units=("units", "sum"),
            gross_revenue=("gross_revenue", "sum"),
            discount_amount=("discount_amount", "sum"),
        )
        .sort_values("month")
    )
    monthly["margin_pct"] = np.where(monthly["revenue"] > 0, monthly["profit"] / monthly["revenue"] * 100, 0.0)
    monthly["discount_leakage"] = monthly["gross_revenue"] - monthly["revenue"]
    monthly["mom_revenue_pct"] = monthly["revenue"].pct_change() * 100
    monthly["mom_profit_pct"] = monthly["profit"].pct_change() * 100
    monthly["mom_margin_pp"] = monthly["margin_pct"].diff()
    return monthly.replace([np.inf, -np.inf], np.nan).fillna(0)


def yoy_comparison(monthly: pd.DataFrame) -> pd.DataFrame:
    """Compare each month with the same month in the prior year when available."""
    frame = monthly.copy()
    frame["year"] = frame["month"].str[:4].astype(int)
    frame["month_num"] = frame["month"].str[5:7].astype(int)
    prior = frame[["year", "month_num", "revenue", "profit", "margin_pct"]].copy()
    prior["year"] += 1
    prior = prior.rename(
        columns={"revenue": "prior_revenue", "profit": "prior_profit", "margin_pct": "prior_margin_pct"}
    )
    out = frame.merge(prior, on=["year", "month_num"], how="left")
    out["yoy_revenue_pct"] = np.where(
        out["prior_revenue"] > 0, (out["revenue"] / out["prior_revenue"] - 1) * 100, np.nan
    )
    out["yoy_profit_pct"] = np.where(
        out["prior_profit"] != 0, (out["profit"] / out["prior_profit"] - 1) * 100, np.nan
    )
    out["yoy_margin_pp"] = out["margin_pct"] - out["prior_margin_pct"]
    return out.drop(columns=["year", "month_num"]).replace([np.inf, -np.inf], np.nan)


def product_economics(df: pd.DataFrame) -> pd.DataFrame:
    """Build product-level revenue, margin, concentration and discount metrics."""
    out = aggregate(df, "product").merge(
        df[["product", "category"]].drop_duplicates(), on="product", how="left"
    )
    total_revenue = df["revenue"].sum()
    out["revenue_share_pct"] = np.where(total_revenue, out["revenue"] / total_revenue * 100, 0.0)
    revenue_median = out["revenue"].median()
    margin_median = out["margin_pct"].median()
    out["commercial_quadrant"] = np.select(
        [
            (out["revenue"] >= revenue_median) & (out["margin_pct"] >= margin_median),
            (out["revenue"] >= revenue_median) & (out["margin_pct"] < margin_median),
            (out["revenue"] < revenue_median) & (out["margin_pct"] >= margin_median),
        ],
        ["Growth Engine", "Revenue Trap", "Margin Specialist"],
        default="Long Tail",
    )
    return out.sort_values("revenue", ascending=False).reset_index(drop=True)


def pareto(df: pd.DataFrame, dimension: str = "product") -> pd.DataFrame:
    """Compute cumulative revenue concentration for a business dimension."""
    out = aggregate(df, dimension).copy()
    total = out["revenue"].sum()
    out["revenue_share_pct"] = np.where(total, out["revenue"] / total * 100, 0.0)
    out["cumulative_share_pct"] = out["revenue_share_pct"].cumsum()
    return out


def mix_shift(df: pd.DataFrame, dimension: str = "category") -> pd.DataFrame:
    """Measure current-year versus prior-year revenue mix by dimension."""
    if dimension not in SAFE_DIMENSIONS:
        raise ValueError(f"Unsupported dimension: {dimension}")
    yearly = df.groupby(["year", dimension], as_index=False)["revenue"].sum()
    totals = yearly.groupby("year")["revenue"].transform("sum")
    yearly["mix_pct"] = np.where(totals > 0, yearly["revenue"] / totals * 100, 0.0)
    years = sorted(yearly["year"].unique())
    if len(years) < 2:
        yearly["mix_shift_pp"] = 0.0
        return yearly
    current, prior = years[-1], years[-2]
    pivot = yearly.pivot(index=dimension, columns="year", values="mix_pct").fillna(0.0).reset_index()
    pivot["mix_shift_pp"] = pivot.get(current, 0.0) - pivot.get(prior, 0.0)
    return pivot.sort_values("mix_shift_pp", ascending=False).reset_index(drop=True)


def discount_intelligence(df: pd.DataFrame) -> pd.DataFrame:
    """Quantify discount intensity and realized economics by discount band."""
    out = (
        df.groupby("discount_band", observed=False, as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            units=("units", "sum"),
            gross_revenue=("gross_revenue", "sum"),
            revenue=("revenue", "sum"),
            profit=("profit", "sum"),
        )
    )
    out["discount_leakage"] = out["gross_revenue"] - out["revenue"]
    out["margin_pct"] = np.where(out["revenue"] > 0, out["profit"] / out["revenue"] * 100, 0.0)
    return out


def anomalies(monthly: pd.DataFrame) -> pd.DataFrame:
    """Flag unusual monthly revenue or margin movement using robust z-scores."""
    out = monthly.copy()
    for column in ("revenue", "margin_pct", "mom_margin_pp"):
        median = out[column].median()
        mad = np.median(np.abs(out[column] - median))
        out[f"{column}_robust_z"] = 0.0 if mad == 0 else 0.6745 * (out[column] - median) / mad
    out["is_unusual"] = out[["revenue_robust_z", "margin_pct_robust_z", "mom_margin_pp_robust_z"]].abs().max(axis=1) >= 3.5
    return out


def recommendations(df: pd.DataFrame) -> list[dict[str, str]]:
    """Generate evidence-based recommendations from computed commercial signals."""
    products = product_economics(df)
    monthly = monthly_trend(df)
    recs: list[dict[str, str]] = []

    low_margin = products[products["revenue"] > products["revenue"].quantile(0.70)].sort_values("margin_pct").head(1)
    if not low_margin.empty:
        row = low_margin.iloc[0]
        recs.append({
            "title": "Protect high-value margin",
            "detail": f"{row['product']} combines high revenue with only {row['margin_pct']:.1f}% margin. Review discounting and unit economics before scaling volume.",
        })

    leakage = products.sort_values("discount_leakage", ascending=False).head(1)
    if not leakage.empty:
        row = leakage.iloc[0]
        recs.append({
            "title": "Target discount leakage",
            "detail": f"{row['product']} has the largest absolute discount leakage at ${row['discount_leakage']:,.0f}. Test tighter discount guardrails or targeted offers.",
        })

    unusual = anomalies(monthly)
    flagged = unusual[unusual["is_unusual"]].sort_values("month").tail(1)
    if not flagged.empty:
        row = flagged.iloc[0]
        recs.append({
            "title": "Investigate unusual movement",
            "detail": f"{row['month']} is statistically unusual on revenue, margin or margin movement. Trace campaign, pricing, mix and supply events before extrapolating the movement.",
        })

    pareto_df = pareto(df)
    threshold = pareto_df[pareto_df["cumulative_share_pct"] <= 80]
    count = max(len(threshold), 1)
    share = float(threshold["revenue_share_pct"].sum()) if not threshold.empty else float(pareto_df.head(1)["revenue_share_pct"].sum())
    recs.append({
        "title": "Focus the commercial portfolio",
        "detail": f"The top {count} products account for approximately {share:.1f}% of revenue. Prioritize these products for availability and pricing reviews.",
    })
    return recs[:4]
