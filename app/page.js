'use client';

import { useEffect, useMemo, useState } from 'react';
import { FILTERS, calculateKpis, filterRows, parseSalesCsv } from './data-utils';

const MONEY = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
const NUMBER = new Intl.NumberFormat('en-US');

function money(value) { return MONEY.format(value || 0); }
function number(value) { return NUMBER.format(value || 0); }
function pct(value) { return `${(value || 0).toFixed(1)}%`; }
function sum(rows, key) { return rows.reduce((total, row) => total + Number(row[key] || 0), 0); }
function unique(rows, key) { return [...new Set(rows.map((row) => row[key]))].sort(); }

function BarChart({ rows, metric }) {
  const max = Math.max(...rows.map((row) => Number(row[metric] || 0)), 1);
  return <div className="bars" aria-label={`${metric} comparison`}>
    {rows.slice(0, 8).map((row) => <div className="bar-row" key={row.label}>
      <div className="bar-meta"><span>{row.label}</span><strong>{metric === 'margin_pct' ? pct(row[metric]) : money(row[metric])}</strong></div>
      <div className="track"><div className="fill" style={{ width: `${Math.max(2, row[metric] / max * 100)}%` }} /></div>
    </div>)}
  </div>;
}

function TrendChart({ rows, metric }) {
  const values = rows.map((row) => Number(row[metric] || 0));
  const max = Math.max(...values, 1); const min = Math.min(...values, 0);
  const w = 820; const h = 280; const pad = 34;
  const points = rows.map((row, index) => {
    const x = pad + (index * (w - 2 * pad)) / Math.max(rows.length - 1, 1);
    const y = h - pad - ((Number(row[metric] || 0) - min) / Math.max(max - min, 1)) * (h - 2 * pad);
    return [x, y];
  });
  const path = points.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
  return <div className="chart-wrap"><svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Monthly performance trend">
    <path d={path} fill="none" stroke="currentColor" strokeWidth="3" />
    {points.map(([x, y], i) => <circle key={rows[i].month} cx={x} cy={y} r="4" fill="currentColor"><title>{`${rows[i].month}: ${metric === 'margin_pct' ? pct(rows[i][metric]) : money(rows[i][metric])}`}</title></circle>)}
  </svg><div className="axis-labels"><span>{rows[0]?.month}</span><span>{rows.at(-1)?.month}</span></div></div>;
}

export default function Home() {
  const [data, setData] = useState(null);
  const [records, setRecords] = useState([]);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({ region: '', channel: '', segment: '', category: '', product: '' });
  const [metric, setMetric] = useState('revenue');
  const [trendMetric, setTrendMetric] = useState('revenue');

  useEffect(() => {
    Promise.all([fetch('/analytics.json', { cache: 'no-store' }), fetch('/data/sales.csv', { cache: 'no-store' })])
      .then(async ([artifactResponse, csvResponse]) => {
        if (!artifactResponse.ok || !csvResponse.ok) throw new Error('Production analytics data could not be loaded.');
        const artifact = await artifactResponse.json();
        const csv = await csvResponse.text();
        setData(artifact); setRecords(parseSalesCsv(csv));
      })
      .catch((cause) => setError(cause.message));
  }, []);

  const filtered = useMemo(() => filterRows(records, filters), [records, filters]);
  const kpis = useMemo(() => ({
    ...calculateKpis(filtered),
    discount: filtered.length ? sum(filtered, 'discount_pct') / filtered.length * 100 : 0,
  }), [filtered]);
  const trend = useMemo(() => {
    const grouped = Object.values(filtered.reduce((acc, row) => {
      acc[row.month] ??= { month: row.month, revenue: 0, profit: 0, units: 0 };
      acc[row.month].revenue += row.revenue; acc[row.month].profit += row.profit; acc[row.month].units += row.units; return acc;
    }, {}));
    return grouped.sort((a, b) => a.month.localeCompare(b.month)).map((row) => ({ ...row, margin_pct: row.revenue ? row.profit / row.revenue * 100 : 0 }));
  }, [filtered]);
  const dimensionRows = useMemo(() => {
    const grouped = Object.values(filtered.reduce((acc, row) => {
      const key = row.category;
      acc[key] ??= { label: key, revenue: 0, profit: 0 };
      acc[key].revenue += row.revenue; acc[key].profit += row.profit;
      return acc;
    }, {}));
    return grouped.map((row) => ({ ...row, margin_pct: row.revenue ? row.profit / row.revenue * 100 : 0 })).sort((a, b) => b[metric] - a[metric]);
  }, [filtered, metric]);
  const filteredProducts = useMemo(() => {
    const grouped = Object.values(filtered.reduce((acc, row) => {
      acc[row.product] ??= { product: row.product, revenue: 0 };
      acc[row.product].revenue += row.revenue; return acc;
    }, {})).sort((a, b) => b.revenue - a.revenue);
    const total = grouped.reduce((value, row) => value + row.revenue, 0); let cumulative = 0;
    return grouped.map((row) => { const share = total ? row.revenue / total * 100 : 0; cumulative += share; return { ...row, revenue_share_pct: share, cumulative_share_pct: cumulative }; }).slice(0, 8);
  }, [filtered]);
  const filteredRecommendations = useMemo(() => {
    if (!filtered.length) return [];
    const products = Object.values(filtered.reduce((acc, row) => {
      acc[row.product] ??= { product: row.product, revenue: 0, profit: 0, gross: 0 };
      acc[row.product].revenue += row.revenue; acc[row.product].profit += row.profit;
      acc[row.product].gross += row.units * (row.revenue / Math.max(1 - row.discount_pct, 0.000001)); return acc;
    }, {}));
    products.forEach((row) => { row.margin = row.revenue ? row.profit / row.revenue * 100 : 0; row.leakage = row.gross - row.revenue; });
    const revenueFloor = [...products].sort((a, b) => a.revenue - b.revenue)[Math.floor(products.length * .7)]?.revenue;
    const highValueLowMargin = [...products].filter((row) => row.revenue >= revenueFloor).sort((a, b) => a.margin - b.margin)[0];
    const leakage = [...products].sort((a, b) => b.leakage - a.leakage)[0];
    const monthly = Object.values(filtered.reduce((acc, row) => { acc[row.month] ??= { month: row.month, revenue: 0 }; acc[row.month].revenue += row.revenue; return acc; }, {}));
    const latest = monthly.sort((a, b) => a.month.localeCompare(b.month)).at(-1);
    return [
      highValueLowMargin && { title: 'Protect high-value margin', detail: `${highValueLowMargin.product} combines high revenue with only ${highValueLowMargin.margin.toFixed(1)}% margin. Review discounting and unit economics before scaling volume.` },
      leakage && { title: 'Target discount leakage', detail: `${leakage.product} has the largest estimated discount leakage at ${money(leakage.leakage)} in this scope.` },
      latest && { title: 'Keep the latest movement in context', detail: `${latest.month} generated ${money(latest.revenue)} revenue. Compare the change with product mix and discount pressure before treating it as structural.` },
    ].filter(Boolean);
  }, [filtered]);

  if (error) return <main className="shell"><section className="state error"><span>●</span><h1>Analytics unavailable</h1><p>{error}</p><button onClick={() => location.reload()}>Retry</button></section></main>;
  if (!data || (data.source?.rows > 0 && records.length === 0)) return <main className="shell"><section className="state"><div className="spinner" /><h1>Loading command center</h1><p>Verifying the production analytics artifact…</p></section></main>;

  const health = data.health?.status === 'healthy' && data.health?.validated_rows === data.source?.rows && records.length === data.source?.rows;
  const options = Object.fromEntries(FILTERS.map((key) => [key, unique(records, key)]));
  const reset = () => setFilters({ region: '', channel: '', segment: '', category: '', product: '' });
  const change = (key, value) => setFilters((current) => ({ ...current, [key]: value }));

  return <main className="shell">
    <header className="hero">
      <div><div className="eyebrow">DAY 01 · 100 DAYS OF DATA SCIENCE</div><h1>Sales Analytics <em>Command Center</em></h1><p>From transactions to commercial decisions. Explore revenue quality, margin pressure, concentration, and growth without losing the evidence trail.</p></div>
      <div className={`health ${health ? 'healthy' : 'unhealthy'}`}><span className="dot" />{health ? 'PIPELINE HEALTHY' : 'PIPELINE CHECK FAILED'}<small>{number(data.health.validated_rows)} validated rows · artifact v{data.schema_version}</small></div>
    </header>
    <section className="filters card"><div className="filter-title"><div><span className="eyebrow">ANALYSIS SCOPE</span><h2>Slice the commercial engine</h2></div><button className="secondary" onClick={reset}>Reset filters</button></div><div className="filter-grid">
      {FILTERS.map((key) => <label key={key}>{key}<select value={filters[key]} onChange={(event) => change(key, event.target.value)}><option value="">All {key}s</option>{options[key].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>)}
    </div></section>
    <section className="kpis">{[['Revenue', money(kpis.revenue)], ['Profit', money(kpis.profit)], ['Margin', pct(kpis.margin)], ['Orders', number(kpis.orders)], ['AOV', money(kpis.aov)], ['Avg discount', pct(kpis.discount)]].map(([label, value]) => <article className="kpi card" key={label}><span>{label}</span><strong>{value}</strong></article>)}</section>
    {filtered.length === 0 ? <section className="state card"><h2>No transactions match this scope</h2><p>Broaden one or more filters to restore the analytical view.</p><button onClick={reset}>Reset filters</button></section> : <>
      <section className="grid two"><article className="card wide"><div className="cardhead"><div><span className="eyebrow">TREND</span><h2>Commercial trajectory</h2></div><select value={trendMetric} onChange={(event) => setTrendMetric(event.target.value)}><option value="revenue">Revenue</option><option value="profit">Profit</option><option value="margin_pct">Margin</option></select></div><TrendChart rows={trend} metric={trendMetric} /></article>
      <article className="card"><span className="eyebrow">EVIDENCE-BASED ACTIONS</span><h2>What deserves attention</h2><div className="insights">{filteredRecommendations.map((item) => <div key={item.title}><b>{item.title}</b><span>{item.detail}</span></div>)}</div></article></section>
      <section className="grid two"><article className="card"><div className="cardhead"><div><span className="eyebrow">MIX</span><h2>Category economics</h2></div><select value={metric} onChange={(event) => setMetric(event.target.value)}><option value="revenue">Revenue</option><option value="profit">Profit</option><option value="margin_pct">Margin</option></select></div><BarChart rows={dimensionRows} metric={metric} /></article>
      <article className="card"><div className="cardhead"><div><span className="eyebrow">CONCENTRATION</span><h2>Product Pareto</h2></div><span className="pill">80% lens</span></div><div className="ranklist">{filteredProducts.map((row, index) => <div key={row.product}><span className="rank">{String(index + 1).padStart(2, '0')}</span><div><b>{row.product}</b><small>{pct(row.revenue_share_pct)} of scoped revenue · {pct(row.cumulative_share_pct)} cumulative</small></div><strong>{money(row.revenue)}</strong></div>)}</div></article></section>
    </>}
    <footer>Reproducible Python analytics pipeline · Next.js production interface · No notebook dependency · Synthetic data relationships documented in README</footer>
  </main>;
}
