/**
 * CBAM Comply — Browser Report Engine
 * Handles ALL computation client-side. Data never leaves the browser.
 */
const CBAM = (() => {
    'use strict';

    // -----------------------------------------------------------------------
    // Load CBAM reference data
    // -----------------------------------------------------------------------
    let _data = null;

    async function loadData() {
        if (_data) return _data;
        const resp = await fetch('js/cbam-data.json');
        _data = await resp.json();
        return _data;
    }

    function getData() {
        if (!_data) throw new Error('CBAM data not loaded yet. Call loadData() first.');
        return _data;
    }

    // -----------------------------------------------------------------------
    // CN code utilities
    // -----------------------------------------------------------------------
    function normalizeCN(code) {
        let c = code.trim().replace(/\s+/g, '');
        // 8 digits → add dots
        if (/^\d{8}$/.test(c)) c = `${c.slice(0,4)}.${c.slice(4,6)}.${c.slice(6)}`;
        return c;
    }

    function findSector(cnCode) {
        const data = getData();
        for (const [key, sector] of Object.entries(data.sectors)) {
            if (sector.cn_codes[cnCode]) return { sectorKey: key, sector, info: sector.cn_codes[cnCode] };
        }
        return null;
    }

    function findCNCodeInData(query) {
        const data = getData();
        const q = query.toLowerCase();
        const results = [];
        for (const [sectorKey, sector] of Object.entries(data.sectors)) {
            for (const [code, info] of Object.entries(sector.cn_codes)) {
                if (code.includes(q) || info.description.toLowerCase().includes(q)) {
                    results.push({ sectorKey, sectorName: sector.name, code, ...info });
                }
            }
        }
        return results;
    }

    // -----------------------------------------------------------------------
    // Emission calculations
    // -----------------------------------------------------------------------
    function calculateGood(good) {
        const { cn_code, quantity, country, actual_emissions, unit } = good;
        const data = getData();

        // Find CN code info
        const found = findSector(cn_code);
        if (!found) throw new Error(`Unknown CN code: ${cn_code}`);

        const defaultEF = found.info.default_ef || 0;
        const ef = (actual_emissions != null && actual_emissions > 0)
            ? actual_emissions : defaultEF;

        const isElectricity = found.sectorKey === 'electricity';
        const qtyUnit = unit || (isElectricity ? 'MWh' : 'tonnes');

        // Country carbon price
        const carbonPrice = data.third_country_carbon_prices[country] || 0;

        // Emissions
        const totalEmissions = quantity * ef;

        // Indirect emissions (scope 2 for electricity)
        let indirectEmissions = 0;
        if (isElectricity) {
            const countryEF = data.country_electricity_ef[country] || 0.45;
            indirectEmissions = quantity * countryEF;
        }

        // Carbon price deduction
        // Deduction in EUR = emissions * carbon price in country of origin
        const deductionEUR = totalEmissions * carbonPrice;

        // Certificates needed
        const euETSPerTonne = data.eu_ets_price_2026 || 85;
        const deductionTonnes = deductionEUR / euETSPerTonne;
        const certificatesNeeded = Math.max(0, totalEmissions - deductionTonnes);

        return {
            cn_code,
            description: found.info.description,
            sector: found.sectorName,
            sectorKey: found.sectorKey,
            quantity,
            unit: qtyUnit,
            country,
            country_name: data.country_names[country] || country,
            emission_factor: +ef.toFixed(4),
            default_ef: defaultEF,
            actual_ef: actual_emissions || null,
            total_emissions: +totalEmissions.toFixed(2),
            indirect_emissions: +indirectEmissions.toFixed(2),
            carbon_price_paid: carbonPrice,
            deduction_eur: +deductionEUR.toFixed(2),
            certificates_needed: +certificatesNeeded.toFixed(2),
        };
    }

    function calculateReport(declarant, goods, year, quarter) {
        const calculated = goods.map(g => calculateGood(g));

        const totals = {
            total_quantity: 0,
            total_emissions: 0,
            total_indirect: 0,
            total_certificates: 0,
            total_deduction: 0,
        };

        const sectorBreakdown = {};

        for (const g of calculated) {
            totals.total_quantity += g.quantity;
            totals.total_emissions += g.total_emissions;
            totals.total_indirect += g.indirect_emissions;
            totals.total_certificates += g.certificates_needed;
            totals.total_deduction += g.deduction_eur;

            if (!sectorBreakdown[g.sectorKey]) {
                sectorBreakdown[g.sectorKey] = { name: g.sector, qty: 0, emissions: 0, certificates: 0 };
            }
            sectorBreakdown[g.sectorKey].qty += g.quantity;
            sectorBreakdown[g.sectorKey].emissions += g.total_emissions;
            sectorBreakdown[g.sectorKey].certificates += g.certificates_needed;
        }

        const data = getData();
        const totalCost = totals.total_certificates * data.eu_ets_price_2026;

        const quarterLabel = `Q${quarter} ${year}`;
        const reportId = `CBAM-${year}Q${quarter}-${declarant.country}-${String(goods.length).padStart(3, '0')}`;
        const now = new Date().toISOString();

        return {
            report_id: reportId,
            declarant: { ...declarant },
            year, quarter,
            quarter_label: quarterLabel,
            goods: calculated,
            sector_breakdown: Object.entries(sectorBreakdown).map(([k, v]) => ({ key: k, ...v })),
            totals: {
                total_quantity_tonnes: +totals.total_quantity.toFixed(2),
                total_embedded_emissions: +totals.total_emissions.toFixed(2),
                total_indirect_emissions: +totals.total_indirect.toFixed(2),
                total_certificates_needed: +totals.total_certificates.toFixed(2),
                total_carbon_price_deduction_eur: +totals.total_deduction.toFixed(2),
                total_certificate_cost_eur: +totalCost.toFixed(2),
                eu_ets_price: data.eu_ets_price_2026,
            },
            generated_at: now,
            status: 'draft',
        };
    }

    // -----------------------------------------------------------------------
    // HTML Report Generator
    // -----------------------------------------------------------------------
    function generateHTML(report) {
        const { declarant: d, goods, sector_breakdown, totals, quarter_label, report_id, generated_at } = report;

        // Goods table
        let goodsRows = '';
        goods.forEach((g, i) => {
            goodsRows += `<tr>
                <td>${i + 1}</td>
                <td>${g.cn_code}</td>
                <td>${escHtml(g.description).slice(0, 60)}</td>
                <td>${g.country}</td>
                <td style="text-align:right">${fmtNum(g.quantity)}</td>
                <td style="text-align:right">${fmtNum(g.emission_factor, 4)}</td>
                <td style="text-align:right">${fmtNum(g.total_emissions)}</td>
                <td style="text-align:right">${fmtNum(g.certificates_needed)}</td>
            </tr>`;
        });

        // Sector breakdown
        let sectorRows = '';
        sector_breakdown.forEach(s => {
            sectorRows += `<tr>
                <td>${escHtml(s.name)}</td>
                <td style="text-align:right">${fmtNum(s.qty)}</td>
                <td style="text-align:right">${fmtNum(s.emissions)}</td>
                <td style="text-align:right">${fmtNum(s.certificates)}</td>
            </tr>`;
        });

        // Carbon deduction rows
        let deductionRows = '';
        let hasDeductions = false;
        goods.forEach(g => {
            if (g.carbon_price_paid > 0) {
                hasDeductions = true;
                deductionRows += `<tr>
                    <td>${escHtml(g.country_name)}</td>
                    <td style="text-align:right">€${fmtNum(g.carbon_price_paid)}</td>
                    <td style="text-align:right">€${fmtNum(g.deduction_eur)}</td>
                </tr>`;
            }
        });

        const dateStr = new Date(generated_at).toLocaleDateString('en-GB', {
            day: 'numeric', month: 'long', year: 'numeric'
        });

        return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CBAM Report — ${quarter_label}</title>
<style>
    @page { size: A4; margin: 2cm; }
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', -apple-system, sans-serif; font-size: 11pt; color: #1a1a2e; background: #fff; padding: 20px; margin: 0; }
    .page { max-width: 210mm; margin: 0 auto; }
    .header { background: linear-gradient(135deg, #1a1a2e, #16213e); color: #fff; padding: 28px 32px; border-radius: 8px; margin-bottom: 28px; }
    .header h1 { margin: 0 0 4px; font-size: 22pt; font-weight: 700; }
    .header .sub { opacity: .8; font-size: 10pt; }
    .summary-box { background: linear-gradient(135deg, #e94560, #c23152); color: #fff; padding: 20px; border-radius: 8px; margin: 20px 0; }
    .summary-grid { display: flex; flex-wrap: wrap; gap: 16px; }
    .summary-item { flex: 1; min-width: 160px; text-align: center; padding: 8px; }
    .summary-item .val { font-size: 20pt; font-weight: 700; display: block; }
    .summary-item .lbl { font-size: 9pt; opacity: .8; }
    h2 { color: #1a1a2e; border-bottom: 2px solid #e94560; padding-bottom: 5px; font-size: 14pt; margin: 24px 0 12px; }
    table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 9.5pt; }
    th { background: #1a1a2e; color: #fff; padding: 8px 6px; text-align: left; font-weight: 600; }
    td { padding: 6px; border-bottom: 1px solid #eee; }
    tr:nth-child(even) { background: #f8f9fa; }
    tfoot td { font-weight: 700; background: #e94560; color: #fff; }
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 16px; }
    .info-grid div { padding: 2px 0; font-size: 10pt; }
    .info-grid strong { display: inline-block; min-width: 140px; color: #555; }
    .declaration { border: 1px solid #ddd; padding: 16px; border-radius: 6px; font-size: 10pt; margin: 16px 0; }
    .watermark { text-align: center; color: #999; font-size: 8pt; border-top: 1px solid #ddd; padding-top: 12px; margin-top: 30px; }
    @media print { body { padding: 0; } .header { border-radius: 0; } }
</style>
</head>
<body>
<div class="page">

<div class="header">
    <h1>CBAM Quarterly Report</h1>
    <div class="sub">EU Carbon Border Adjustment Mechanism — Permanent Regime</div>
    <div class="sub" style="margin-top:6px;font-size:10pt">${quarter_label} | Generated: ${dateStr}</div>
    <div class="sub" style="margin-top:3px;font-size:9pt">Report ID: ${report_id} | Status: <strong>Draft</strong></div>
</div>

<div class="summary-box">
    <div class="summary-grid">
        <div class="summary-item"><span class="val">${fmtNum(totals.total_embedded_emissions)}</span><span class="lbl">Total Emissions (tCO₂e)</span></div>
        <div class="summary-item"><span class="val">${fmtNum(totals.total_certificates_needed)}</span><span class="lbl">CBAM Certificates</span></div>
        <div class="summary-item"><span class="val">€${fmtNum(totals.total_certificate_cost_eur)}</span><span class="lbl">Cost @ €${totals.eu_ets_price}/tCO₂e</span></div>
        <div class="summary-item"><span class="val">${fmtNum(totals.total_quantity_tonnes)}</span><span class="lbl">Total Quantity (t/MWh)</span></div>
    </div>
</div>

<h2>Declarant</h2>
<div class="info-grid">
    <div><strong>Company:</strong> ${escHtml(d.company_name)}</div>
    <div><strong>EORI:</strong> ${escHtml(d.company_eori)}</div>
    <div><strong>VAT:</strong> ${escHtml(d.vat_number)}</div>
    <div><strong>IČO:</strong> ${escHtml(d.registration_number || '—')}</div>
    <div><strong>Address:</strong> ${escHtml(d.address)}</div>
    <div><strong>City:</strong> ${escHtml(d.city)}, ${escHtml(d.postal_code)}</div>
    <div><strong>Country:</strong> ${escHtml(d.country)}</div>
    <div><strong>Contact:</strong> ${escHtml(d.contact_person)}</div>
    <div><strong>Email:</strong> ${escHtml(d.contact_email)}</div>
</div>

<h2>Breakdown by Sector</h2>
<table>
    <thead><tr><th>Sector</th><th style="text-align:right">Qty (t)</th><th style="text-align:right">Emissions</th><th style="text-align:right">Certificates</th></tr></thead>
    <tbody>${sectorRows}</tbody>
    <tfoot><tr><td>TOTAL</td><td style="text-align:right">${fmtNum(totals.total_quantity_tonnes)}</td><td style="text-align:right">${fmtNum(totals.total_embedded_emissions)}</td><td style="text-align:right">${fmtNum(totals.total_certificates_needed)}</td></tr></tfoot>
</table>

<h2>Detailed Import Declaration</h2>
<table>
    <thead><tr><th>#</th><th>CN Code</th><th>Description</th><th>Orig</th><th style="text-align:right">Qty</th><th style="text-align:right">EF</th><th style="text-align:right">tCO₂e</th><th style="text-align:right">Cert</th></tr></thead>
    <tbody>${goodsRows}</tbody>
    <tfoot><tr><td colspan="4">TOTAL</td><td style="text-align:right">${fmtNum(totals.total_quantity_tonnes)}</td><td></td><td style="text-align:right">${fmtNum(totals.total_embedded_emissions)}</td><td style="text-align:right">${fmtNum(totals.total_certificates_needed)}</td></tr></tfoot>
</table>

${hasDeductions ? `<h2>Carbon Price Deduction</h2>
<table>
    <tr><th>Country</th><th style="text-align:right">Price (EUR/t)</th><th style="text-align:right">Deduction</th></tr>
    ${deductionRows}
    <tr style="font-weight:700"><td>TOTAL</td><td></td><td style="text-align:right">€${fmtNum(totals.total_carbon_price_deduction_eur)}</td></tr>
</table>` : ''}

<h2>Declaration</h2>
<div class="declaration">
    I, the undersigned, declare that the information in this CBAM quarterly report is accurate and complete in accordance with Regulation (EU) 2023/956.
</div>
<div class="info-grid" style="margin-top:12px;">
    <div><strong>Place:</strong> ${escHtml(d.city)}, ${escHtml(d.country)}</div>
    <div><strong>Date:</strong> ${dateStr}</div>
    <div><strong>Declarant:</strong> ${escHtml(d.contact_person)}</div>
</div>

<div class="watermark">
    Generated by CBAM Comply — DanceNitra © 2026.<br>
    Based on EU Regulation 2023/956 and Commission Implementing Regulation (EU) 2025/177.
</div>
</div>
</body>
</html>`;
    }

    // -----------------------------------------------------------------------
    // CSV Parsing (browser-native)
    // -----------------------------------------------------------------------
    function parseCSV(text) {
        // Simple CSV parser that handles quoted fields
        const lines = text.split(/\r?\n/).filter(l => l.trim());
        if (lines.length < 2) throw new Error('CSV must have header + at least one data row');

        const headers = parseCSVLine(lines[0]);
        const rows = [];
        for (let i = 1; i < lines.length; i++) {
            const vals = parseCSVLine(lines[i]);
            if (vals.length === 0 || vals.every(v => !v.trim())) continue;
            const row = {};
            headers.forEach((h, idx) => { row[h.trim()] = (vals[idx] || '').trim(); });
            rows.push(row);
        }
        return rows;
    }

    function parseCSVLine(line) {
        const result = [];
        let current = '';
        let inQuotes = false;
        for (let i = 0; i < line.length; i++) {
            const ch = line[i];
            if (ch === '"') {
                if (inQuotes && i + 1 < line.length && line[i + 1] === '"') {
                    current += '"'; i++;
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (ch === ',' && !inQuotes) {
                result.push(current);
                current = '';
            } else {
                current += ch;
            }
        }
        result.push(current);
        return result;
    }

    // -----------------------------------------------------------------------
    // Excel parsing (XLSX)
    // -----------------------------------------------------------------------
    async function parseExcel(file) {
        // Use SheetJS loaded from CDN
        if (typeof XLSX === 'undefined') {
            await loadScript('https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js');
        }
        const data = await file.arrayBuffer();
        const workbook = XLSX.read(data, { type: 'array' });
        const sheet = workbook.Sheets[workbook.SheetNames[0]];
        const json = XLSX.utils.sheet_to_json(sheet, { defval: '' });
        return json;
    }

    // -----------------------------------------------------------------------
    // Column mapping (smart matching)
    // -----------------------------------------------------------------------
    const COLUMN_MAP = {
        cn_code: ['cn_code', 'cn code', 'cncode', 'taric', 'tariff', 'hscode', 'hs code', 'hs', 'commodity code', 'product code', 'code', 'customs code'],
        quantity: ['quantity', 'qty', 'net mass', 'netmass', 'net weight', 'net_weight', 'netweight', 'weight', 'kg', 'tonnes', 'tons', 'mt', 'gross weight'],
        country: ['country', 'country of origin', 'origin', 'origin_country', 'coo', 'country_code', 'cntry', 'origin code'],
        description: ['description', 'descr', 'desc', 'product_name', 'product', 'goods description', 'item description', 'text', 'name'],
        actual_emissions: ['actual_emissions', 'actual emission', 'actual_em', 'verified emissions', 'real emissions', 'co2 factor', 'ef', 'emission factor'],
        unit: ['unit', 'uom', 'unit of measure', 'measure unit', 'quantity unit'],
    };

    function mapColumns(row) {
        const mapped = {};
        const keys = Object.keys(row);
        for (const [field, aliases] of Object.entries(COLUMN_MAP)) {
            for (const alias of aliases) {
                const key = keys.find(k => k.trim().toLowerCase() === alias.toLowerCase());
                if (key) { mapped[field] = row[key]; break; }
            }
        }
        // Keep all original fields too
        return { ...row, ...mapped };
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------
    function fmtNum(n, decimals = 2) {
        if (n == null || isNaN(n)) return '0';
        return Number(n).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    }

    function escHtml(s) {
        if (!s) return '';
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function loadScript(src) {
        return new Promise((resolve, reject) => {
            const s = document.createElement('script');
            s.src = src;
            s.onload = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    // -----------------------------------------------------------------------
    // Public API
    // -----------------------------------------------------------------------
    return {
        loadData,
        normalizeCN,
        findSector,
        findCNCodeInData,
        calculateGood,
        calculateReport,
        generateHTML,
        parseCSV,
        parseExcel,
        mapColumns,
        fmtNum,
        escHtml,
    };
})();
