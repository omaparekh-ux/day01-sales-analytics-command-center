# Day 01 · Sales Analytics Command Center

A portfolio-grade commercial intelligence product that turns transaction-level sales data into evidence-backed decisions about revenue quality, profitability, discount pressure, concentration, mix shifts and unusual performance.

## Portfolio thesis

This is intentionally **not a static sales dashboard**. The Python analytics layer is the source of truth, while the Next.js interface exposes the resulting decision layer. The project demonstrates data validation, reproducible analytics engineering, business statistics, commercial reasoning, responsive product design, testing and CI/CD practices.

## Business problem

Leadership often sees revenue growth without understanding whether that growth is profitable, whether discounting is destroying economics, whether product mix is shifting, or whether a recent movement is statistically unusual.

The command center answers:

- Where is revenue growing?
- Where is growth profitable or margin dilutive?
- Which products are **Growth Engines**, **Revenue Traps**, **Margin Specialists** or **Long Tail** products?
- How much revenue is being surrendered through discounts?
- Which channels and segments carry the most discount pressure?
- How concentrated is revenue across products?
- Which categories/channels/segments are gaining or losing revenue mix?
- Which monthly movements are unusual enough to investigate?
- What should a commercial leader investigate next?

## Architecture

```text
Deterministic transaction generator / CSV source
                 ↓
        Validation + enrichment
                 ↓
       Commercial analytics engine
                 ↓
     Reproducible analytics artifact
                 ↓
         Next.js decision UI
                 ↓
       Interactive filtering + views
```

The frontend never invents business conclusions. The artifact records source metadata and validation status. Generated source data and analytics artifacts can be rebuilt deterministically from the committed generator.

## Dataset

The project uses a deterministic synthetic retail transaction model spanning January 2024 through June 2025. The canonical generator is seed-controlled (`SEED = 42`) and defaults to **5,000 transactions** so the analytical workflow is large enough to support meaningful distributions, concentration analysis, mix analysis and anomaly screening.

The synthetic relationships are deliberately documented rather than presented as real market facts. They include product-specific price/cost bands, region/channel/segment mix, discount behavior and calendar variation. The generator adds noise and variation rather than manufacturing a predetermined business winner.

### Data dictionary

| Field | Meaning |
|---|---|
| `order_id` | Unique transaction identifier |
| `order_date` | UTC transaction date |
| `region` | Commercial region |
| `channel` | Sales channel |
| `segment` | Customer segment |
| `category` | Product category |
| `product` | Product name |
| `units` | Units sold |
| `unit_price` | List price per unit |
| `discount_pct` | Discount applied, 0–1 |
| `unit_cost` | Cost per unit |

## Analytics methodology

### Core economics

- Gross revenue
- Realized revenue
- Discount amount / leakage
- Cost
- Gross profit
- Gross margin
- Orders
- Units
- Average order value
- Realized revenue per unit

### Growth

- Month-over-month revenue growth
- Month-over-month profit growth
- Month-over-month margin movement in percentage points
- Year-over-year revenue growth
- Year-over-year profit growth
- Year-over-year margin movement

### Commercial intelligence

- Product economics
- Category economics
- Region economics
- Channel economics
- Segment economics
- Revenue concentration
- Pareto analysis
- Product commercial quadrants
- Discount intensity bands
- Mix-shift analysis

### Product quadrants

Products are classified relative to the portfolio median into:

- **Growth Engine:** high revenue + high margin
- **Revenue Trap:** high revenue + lower margin
- **Margin Specialist:** lower revenue + high margin
- **Long Tail:** lower revenue + lower margin

This is a descriptive decision framework, not a causal model.

### Discount intelligence

Discount bands are evaluated for:

- order volume
- units
- gross revenue
- realized revenue
- discount leakage
- profit
- margin

The goal is to quantify the economic cost of discounting rather than simply reporting an average discount rate.

### Mix shift

The analytics engine compares annual revenue mix by:

- category
- channel
- segment

and reports the change in percentage points between the latest two years when sufficient history exists.

### Anomaly screening

Monthly revenue, margin and margin movement are screened using robust MAD-based scores. The output is a descriptive investigation signal, not a causal explanation.

## Evidence-based recommendations

Recommendations are generated from computed metrics. They include:

- protecting high-value margin
- targeting discount leakage
- investigating statistically unusual movements
- focusing the commercial portfolio using revenue concentration

The system does not fabricate recommendations or hardcode a business conclusion.

## Reproducibility

Install Python dependencies and rebuild the pipeline:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python -m src.generate_data
python -m src.build_artifacts
pytest
```

`src.generate_data` is deterministic. `src.build_artifacts` validates, enriches and serializes the production analytics artifact to `public/analytics.json`.

The GitHub Actions workflow `refresh-generated-artifacts.yml` is responsible for refreshing the generated source snapshot and analytics artifact from the canonical generator so that committed generated outputs remain reproducible rather than manually assembled.

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

## Quality gates

The repository includes GitHub Actions for:

- Python dependency installation
- artifact generation
- pytest
- Ruff
- frontend tests
- ESLint
- Prettier validation
- Next.js production build
- npm dependency audit

Meaningful tests cover data validation, analytical calculations, reproducibility and frontend transformations. The repository intentionally avoids unnecessary notebook files.

## Product design

The command center is a dense executive analytics interface designed around decision flow rather than decorative dashboard elements. It includes:

- five-dimensional filtering
- revenue/profit/margin metric switching
- trend analysis
- evidence-based recommendations
- product Pareto concentration
- responsive layout
- loading state
- error state
- empty-filter state
- reset controls
- keyboard-visible focus
- accessible labels and chart descriptions
- data-backed pipeline-health status

## Security and engineering

- No secrets are committed.
- `.env.example` documents environment configuration where required.
- Business dimensions are allow-listed before aggregation.
- Numeric values are checked for finite values and valid commercial ranges.
- Dependencies are audited in CI.
- Production artifacts are generated from source rather than manually edited.
- MIT licensed.

## Limitations

- The dataset is synthetic and cannot establish real market benchmarks.
- The anomaly detector is a screening mechanism, not a causal detector.
- Product quadrants are relative to the current portfolio and should not be interpreted as universal classifications.
- Mix shift is descriptive and does not establish why the mix changed.
- Client-side filtering is appropriate for this portfolio-scale artifact, not for billions of rows.
- Recommendations are decision-support prompts, not autonomous commercial actions.

## Future improvements

- SQL-backed semantic layer with query lineage
- Causal discount and price-elasticity experiments
- role-specific executive/category-manager views
- automated data-drift monitoring
- scheduled production data refresh
- server-side analytical querying for large datasets

## License

MIT. See `LICENSE`.
