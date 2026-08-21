"""Generate the deterministic synthetic retail source dataset."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
DEFAULT_ROWS = 5_000


def generate(n: int = DEFAULT_ROWS) -> pd.DataFrame:
    """Generate reproducible transaction-level retail data with realistic commercial variation."""
    if n < 1:
        raise ValueError("n must be positive")

    rng = np.random.default_rng(SEED)
    regions = np.array(["North", "South", "East", "West"])
    channels = np.array(["Online", "Retail", "Distributor"])
    segments = np.array(["Enterprise", "SMB", "Consumer"])
    categories = {
        "Technology": ["Laptop Pro", "Monitor 27", "Keyboard", "Docking Station"],
        "Office": ["Ergo Chair", "Standing Desk", "Webcam", "Desk Lamp"],
        "Accessories": ["USB Hub", "Headset", "Mouse", "Power Bank"],
    }
    cats = list(categories)
    dates = pd.date_range("2024-01-01", "2025-06-30", freq="D", tz="UTC")

    region = rng.choice(regions, n, p=[0.23, 0.29, 0.18, 0.30])
    channel = rng.choice(channels, n, p=[0.47, 0.28, 0.25])
    segment = rng.choice(segments, n, p=[0.18, 0.37, 0.45])
    category = rng.choice(cats, n, p=[0.46, 0.34, 0.20])
    product = np.array([rng.choice(categories[c]) for c in category])

    base_price = {
        "Laptop Pro": 950, "Monitor 27": 310, "Keyboard": 85, "Docking Station": 190,
        "Ergo Chair": 420, "Standing Desk": 560, "Webcam": 120, "Desk Lamp": 70,
        "USB Hub": 45, "Headset": 95, "Mouse": 55, "Power Bank": 80,
    }
    base_cost = {key: value * rng.uniform(0.53, 0.76) for key, value in base_price.items()}

    segment_lambda = np.where(segment == "Enterprise", 4, np.where(segment == "SMB", 3, 2))
    units = rng.poisson(segment_lambda) + 1
    price = np.array([base_price[p] for p in product]) * rng.normal(1, 0.06, n)
    discount_mean = np.where(
        channel == "Distributor",
        0.16,
        np.where(segment == "Enterprise", 0.11, 0.07),
    )
    discount = np.clip(rng.normal(discount_mean, 0.035, n), 0, 0.30)
    cost = np.array([base_cost[p] for p in product]) * rng.normal(1, 0.025, n)

    day_index = rng.integers(0, len(dates), n)
    order_date = dates[day_index]
    seasonal = 1 + 0.10 * np.sin(2 * np.pi * order_date.dayofyear.to_numpy() / 365.25)
    units = np.maximum(1, np.round(units * seasonal).astype(int))

    return pd.DataFrame({
        "order_id": [f"ORD-{i:06d}" for i in range(1, n + 1)],
        "order_date": order_date,
        "region": region,
        "channel": channel,
        "segment": segment,
        "category": category,
        "product": product,
        "units": units,
        "unit_price": np.round(price, 2),
        "discount_pct": np.round(discount, 4),
        "unit_cost": np.round(cost, 2),
    })


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    output = root / "data" / "sales.csv"
    output.parent.mkdir(exist_ok=True)
    generate().to_csv(output, index=False)
    print(f"Wrote {output} with {DEFAULT_ROWS:,} rows using seed {SEED}")
