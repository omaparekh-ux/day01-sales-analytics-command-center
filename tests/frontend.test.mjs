import test from 'node:test';
import assert from 'node:assert/strict';
import { calculateKpis, filterRows, parseSalesCsv } from '../app/data-utils.js';

const csv = `order_id,order_date,region,channel,segment,category,product,units,unit_price,discount_pct,unit_cost\nA,2025-01-01T00:00:00Z,West,Online,SMB,Technology,Laptop,2,100,0.1,60\nB,2025-01-02T00:00:00Z,East,Retail,Consumer,Office,Chair,1,200,0.2,100`;

test('parses sales CSV and derives transaction economics', () => {
  const rows = parseSalesCsv(csv);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].revenue, 180);
  assert.equal(rows[0].profit, 60);
});

test('filters preserve only the requested commercial scope', () => {
  const rows = parseSalesCsv(csv);
  assert.equal(filterRows(rows, { region: 'West', channel: '', segment: '', category: '', product: '' }).length, 1);
});

test('KPI transformation returns correct revenue and margin', () => {
  const kpis = calculateKpis(parseSalesCsv(csv));
  assert.equal(kpis.revenue, 340);
  assert.equal(kpis.profit, 120);
  assert.equal(Number(kpis.margin.toFixed(2)), 35.29);
});
