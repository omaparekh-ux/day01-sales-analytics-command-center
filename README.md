# Day 01 · Sales Analytics Command Center

A portfolio-grade commercial analytics system that turns transaction-level retail data into reproducible revenue, profitability, discount, concentration, growth, anomaly and decision-support insights.

## Why this project exists

Sales teams often have plenty of transactions but poor visibility into **where growth is profitable, where discounts are eroding economics, which products deserve attention, and whether a recent movement is unusual**. This project creates a compact decision layer rather than another static sales dashboard.

## Architecture

```text
CSV source
   ↓
src.analytics validation + enrichment
   ↓
src.build_artifacts
   ↓
public/analytics.json  ← deterministic production artifact
   ↓
Next.js client dashboard
   ↓
filters → recalculated KPIs/trends/mix
```

The Python layer is the source of truth. The frontend never invents business conclusions. The production artifact records the source SHA-256, row count, schema version and validation state.

## Data

The dataset is a professionally designed synthetic retail transaction dataset covering **1,000 orders from January 2024 through June 2025**. It is used because the project needs a reproducible dataset with commercially meaningful dimensions without exposing proprietary customer data.

Deliberately simulated relationships include varying category mix, region/channel/segment composition, product-level price/cost bands, realistic discount dispersion and calendar variation. These relationships are documented so they are not mistaken for external market facts. The analysis is deterministic from the committed CSV and seed-controlled generator.

### Data dictionary

| Field | Meaning |
|---|---|
| order_id | Unique transaction identifier |
| order_date | UTC transaction date |
| region | Commercial region |
| channel | Sales channel |
| segment | Customer segment |
| category | Product category |
| product | Product name |
| units | Units sold |
| unit_price | List price per unit |
| discount_pct | Discount applied, 0–1 |
| unit_cost | Cost per unit |

## Analytics methodology

The pipeline validates required columns, nulls, dates, numeric types, duplicate orders, quantity/price/cost rules and discount bounds. It then derives gross revenue, realized revenue, cost, profit, margin, time dimensions and discount leakage.

The analytical layer covers:

- MoM revenue and profit growth
- YoY comparisons when prior-year months exist
- Revenue versus profit and gross-margin trends
- Discount leakage and margin erosion
- Category, product, region, channel and segment economics
- High-revenue / low-margin product detection
- Revenue concentration and Pareto analysis
- Unusual monthly revenue/margin movements using robust MAD-based scores
- Evidence-based commercial recommendations

## Reproducible build

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python -m src.build_artifacts
pytest
```

The committed `public/analytics.json` is generated from `data/sales.csv` using the build command. Tests verify deterministic artifact generation.

## Frontend

```bash
npm install
npm run test:frontend
npm run dev
```

Production checks:

```bash
npm run lint
npm run format:check
npm run build
npm audit --audit-level=high
npm start
```

## Quality and CI

GitHub Actions runs the Python artifact build/tests/ruff checks and the frontend install/test/lint/format/build/security audit on pushes and pull requests. On the initial clean checkout, CI also generates the npm lockfile and commits it through the GitHub Actions bot; subsequent builds use the committed lockfile.

## Product design

The command center is intentionally dark, dense and executive-focused. The interface supports date/dimension filtering, revenue/profit/margin views, reset behavior, loading/error/empty states, keyboard-visible focus, responsive layouts and tooltips on trend points. The pipeline-health badge is derived from artifact metadata and loaded-row verification rather than hardcoded.

## Limitations

- The dataset is synthetic and therefore cannot be used to infer real market benchmarks.
- The anomaly detector is a descriptive screening mechanism, not a causal model.
- Filtered frontend calculations are client-side and intended for a portfolio-scale dataset, not billions of rows.
- Recommendations are analytical prompts for commercial review, not autonomous pricing decisions.

## Future improvements

- Add SQL-backed semantic layer and query lineage.
- Add causal discount analysis and price elasticity experiments.
- Add role-based executive/category-manager views.
- Add automated data-drift monitoring and scheduled artifact refresh.

## License

MIT. See `LICENSE`.
