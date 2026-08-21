"""Build the deterministic production analytics artifact from the source CSV."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from .analytics import (
    aggregate,
    anomalies,
    discount_intelligence,
    enrich,
    kpis,
    load_sales,
    mix_shift,
    pareto,
    product_economics,
    recommendations,
    validate_sales,
    monthly_trend,
    yoy_comparison,
)

ROOT = Path(__file__).resolve().parents[1]


def _safe_records(frame: pd.DataFrame) -> list[dict]:
    """Convert dataframe rows to JSON-safe Python values, preserving missingness."""
    clean = frame.copy().astype(object).where(pd.notna(frame), None)
    for column in clean.columns:
        clean[column] = clean[column].map(
            lambda value: value.isoformat() if isinstance(value, pd.Timestamp) else value
        )
    return clean.to_dict(orient="records")


def build(source: Path, destination: Path) -> dict:
    """Validate, enrich and serialize deterministic analytics outputs."""
    raw = load_sales(str(source))
    validate_sales(raw)
    df = enrich(raw)
    monthly = monthly_trend(df)
    yoy = yoy_comparison(monthly)
    products = product_economics(df)
    artifact = {
        "schema_version": "1.2",
        "source": {
            "file": str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "rows": len(raw),
        },
        "health": {
            "status": "healthy",
            "validated_rows": len(df),
            "validated_at_build": True,
        },
        "kpis": kpis(df).to_dict(),
        "monthly": _safe_records(monthly),
        "yoy": _safe_records(yoy),
        "products": _safe_records(products),
        "pareto": _safe_records(pareto(df)),
        "anomalies": _safe_records(anomalies(monthly)),
        "discount_intelligence": _safe_records(discount_intelligence(df)),
        "mix_shift": {
            dimension: _safe_records(mix_shift(df, dimension))
            for dimension in ["category", "channel", "segment"]
        },
        "dimensions": {
            dim: _safe_records(aggregate(df, dim))
            for dim in ["category", "region", "channel", "segment"]
        },
        "recommendations": recommendations(df),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/sales.csv")
    parser.add_argument("--destination", type=Path, default=ROOT / "public/analytics.json")
    args = parser.parse_args()
    artifact = build(args.source, args.destination)
    print(f"Built {args.destination} with {artifact['health']['validated_rows']:,} validated rows")


if __name__ == "__main__":
    main()
