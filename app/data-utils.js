export const FILTERS = ['region', 'channel', 'segment', 'category', 'product'];

export function parseSalesCsv(csv) {
  const lines = csv.trim().split(/\r?\n/);
  const headers = lines.shift().split(',');
  return lines.map((line) => {
    const values = line.match(/(?:[^,\"]|\"[^\"]*\")+/g) || [];
    const row = Object.fromEntries(headers.map((header, index) => [header, (values[index] || '').replace(/^\"|\"$/g, '')]));
    const units = Number(row.units);
    const unitPrice = Number(row.unit_price);
    const discount = Number(row.discount_pct);
    const unitCost = Number(row.unit_cost);
    const revenue = units * unitPrice * (1 - discount);
    return {
      ...row,
      units,
      unit_price: unitPrice,
      discount_pct: discount,
      unit_cost: unitCost,
      revenue: Number(revenue.toFixed(6)),
      profit: Number((revenue - units * unitCost).toFixed(6)),
      month: row.order_date.slice(0, 7),
    };
  });
}

export function filterRows(rows, filters) {
  return rows.filter((row) => FILTERS.every((key) => !filters[key] || row[key] === filters[key]));
}

export function calculateKpis(rows) {
  const revenue = rows.reduce((total, row) => total + row.revenue, 0);
  const profit = rows.reduce((total, row) => total + row.profit, 0);
  const orders = new Set(rows.map((row) => row.order_id)).size;
  return {
    revenue,
    profit,
    margin: revenue ? profit / revenue * 100 : 0,
    orders,
    units: rows.reduce((total, row) => total + row.units, 0),
    aov: orders ? revenue / orders : 0,
  };
}
