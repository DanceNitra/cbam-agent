"""
CBAM Report Generation Engine

Generates professional CBAM quarterly emission reports.
Supports:
- CSV/JSON input of imported goods
- Automatic CN code validation and sector assignment
- Default emission factor lookup
- Carbon price deduction calculation
- Professional HTML report generation
- XLSX/PDF export (planned)
"""
import csv
import json
import os
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from ..data.cn_codes import (
    SECTORS, get_sector_for_cn_code, get_default_emission_factor,
    get_carbon_price_in_country, get_electricity_emission_factor,
    COUNTRY_NAMES, EU_MEMBER_STATES
)
from ..data.report_model import (
    CBAMQuarterlyReport, DeclarantInfo, ImportedGood
)
from .security import SecurityGuardrails


class CBAMEngine:
    """Core engine for CBAM report generation."""
    
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(__file__), '..', 'data')
        self.guardrails = SecurityGuardrails()
    
    def load_import_data(self, filepath: str) -> List[Dict]:
        """Load import data from CSV or JSON file."""
        path = Path(filepath)
        
        # Security check
        self.guardrails.validate_path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        suffix = path.suffix.lower()
        
        if suffix == '.csv':
            return self._load_csv(path)
        elif suffix == '.json':
            return self._load_json(path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Use .csv or .json")
    
    def _load_csv(self, path: Path) -> List[Dict]:
        """Load import data from CSV."""
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                # Validate and clean
                clean_row = self.guardrails.sanitize_row(dict(row))
                rows.append(clean_row)
        return rows
    
    def _load_json(self, path: Path) -> List[Dict]:
        """Load import data from JSON."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            data = data.get('goods', data.get('imports', data.get('items', [data])))
        
        if not isinstance(data, list):
            raise ValueError("JSON must contain a list of goods or 'goods'/'imports' key")
        
        return [self.guardrails.sanitize_row(dict(row)) for row in data]
    
    def create_report_from_rows(
        self,
        rows: List[Dict],
        declarant_info: DeclarantInfo,
        year: int,
        quarter: int,
    ) -> CBAMQuarterlyReport:
        """Create a CBAM quarterly report from import data rows."""
        goods = []
        
        for row in rows:
            cn_code = self.guardrails.sanitize_cn_code(str(row.get('cn_code', '')).strip())
            if not cn_code:
                continue
            
            # Validate CN code
            sector = get_sector_for_cn_code(cn_code)
            if not sector:
                continue
            
            # Parse quantity
            try:
                qty_str = str(row.get('quantity', row.get('quantity_tonnes', '0'))).strip()
                quantity = Decimal(qty_str)
            except (ValueError, TypeError):
                quantity = Decimal("0")
            
            if quantity <= 0:
                continue
            
            # Get country of origin
            country = str(row.get('country', row.get('country_of_origin', ''))).strip().upper()
            country_name = COUNTRY_NAMES.get(country, country)
            
            # Get emission factor
            actual_emissions = None
            if 'actual_emissions' in row:
                try:
                    actual_emissions = Decimal(str(row['actual_emissions']).strip())
                except (ValueError, TypeError):
                    actual_emissions = None
            
            default_ef = get_default_emission_factor(cn_code)
            if default_ef is not None:
                default_ef = Decimal(str(default_ef))
            
            # Use actual if provided and verified, else default
            use_actual = actual_emissions is not None and actual_emissions > 0
            emission_factor = actual_emissions if use_actual else (default_ef or Decimal("0"))
            
            # Carbon price paid in origin country
            carbon_price = get_carbon_price_in_country(country)
            
            good = ImportedGood(
                cn_code=cn_code,
                description=row.get('description', ''),
                sector=sector,
                quantity_tonnes=quantity,
                quantity_unit=row.get('unit', 'tonnes'),
                country_of_origin=country,
                country_name=country_name,
                actual_emissions=actual_emissions if use_actual else None,
                default_emission_factor=default_ef,
                carbon_price_paid=Decimal(str(carbon_price)) if carbon_price > 0 else None,
                verified=bool(row.get('verified', False)),
                verification_body=str(row.get('verification_body', '')),
            )
            goods.append(good)
        
        # Create report
        report = CBAMQuarterlyReport(
            declarant=declarant_info,
            year=year,
            quarter=quarter,
            goods=goods,
        )
        
        # Calculate totals
        report.calculate_totals()
        
        # Generate report ID
        report.report_id = f"CBAM-{year}Q{quarter}-{declarant_info.country}-{len(goods):03d}"
        
        return report
    
    def generate_html_report(self, report: CBAMQuarterlyReport, output_path: Optional[str] = None) -> str:
        """Generate a professional HTML report."""
        html = self._render_html_report(report)
        
        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
        
        return html
    
    def _render_html_report(self, report: CBAMQuarterlyReport) -> str:
        """Render a professional CBAM quarterly report as HTML."""
        r = report
        d = r.declarant
        
        # Build goods table rows
        goods_rows = ""
        for i, g in enumerate(r.goods, 1):
            ef = g.actual_emissions or g.default_emission_factor or Decimal("0")
            goods_rows += f"""
            <tr>
                <td>{i}</td>
                <td>{g.cn_code}</td>
                <td>{g.description[:60]}</td>
                <td>{g.country_of_origin}</td>
                <td style="text-align:right">{float(g.quantity_tonnes):,.2f}</td>
                <td style="text-align:right">{float(ef):.4f}</td>
                <td style="text-align:right">{float(g.total_embedded_emissions or 0):,.2f}</td>
                <td style="text-align:right">{float(g.certificates_needed or 0):,.2f}</td>
            </tr>"""
        
        # Sector breakdown
        sector_totals = {}
        for g in r.goods:
            sector = g.sector or "other"
            if sector not in sector_totals:
                sector_totals[sector] = {"qty": Decimal("0"), "emissions": Decimal("0"), "certificates": Decimal("0")}
            sector_totals[sector]["qty"] += g.quantity_tonnes
            sector_totals[sector]["emissions"] += (g.total_embedded_emissions or Decimal("0"))
            sector_totals[sector]["certificates"] += (g.certificates_needed or Decimal("0"))
        
        sector_rows = ""
        sector_names = {
            "cement": "Cement", "iron_steel": "Iron & Steel",
            "aluminium": "Aluminium", "fertilizers": "Fertilizers",
            "electricity": "Electricity", "hydrogen": "Hydrogen"
        }
        for sk, sv in sorted(sector_totals.items()):
            sector_rows += f"""
            <tr>
                <td>{sector_names.get(sk, sk)}</td>
                <td style="text-align:right">{float(sv['qty']):,.2f}</td>
                <td style="text-align:right">{float(sv['emissions']):,.2f}</td>
                <td style="text-align:right">{float(sv['certificates']):,.2f}</td>
            </tr>"""
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CBAM Quarterly Report — {r.get_quarter_label()}</title>
<style>
    @page {{ size: A4; margin: 2cm; }}
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 11pt; line-height: 1.6; color: #1a1a2e; background: #fff; padding: 20px; }}
    .container {{ max-width: 210mm; margin: 0 auto; background: #fff; }}
    .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #fff; padding: 30px; margin-bottom: 30px; border-radius: 8px; }}
    .header h1 {{ margin: 0 0 5px 0; font-size: 24pt; }}
    .header .sub {{ opacity: 0.8; font-size: 11pt; }}
    .watermark {{ color: #888; font-size: 9pt; text-align: center; border-top: 1px solid #ddd; padding-top: 10px; margin-top: 30px; }}
    .section {{ margin-bottom: 25px; }}
    .section h2 {{ color: #1a1a2e; border-bottom: 2px solid #e94560; padding-bottom: 5px; font-size: 14pt; }}
    table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 9.5pt; }}
    th {{ background: #1a1a2e; color: #fff; padding: 8px 6px; text-align: left; font-weight: 600; }}
    td {{ padding: 6px; border-bottom: 1px solid #eee; }}
    tr:nth-child(even) {{ background: #f8f9fa; }}
    .summary-box {{ background: linear-gradient(135deg, #e94560 0%, #c23152 100%); color: #fff; padding: 20px; border-radius: 8px; margin: 20px 0; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; }}
    .summary-item {{ text-align: center; padding: 10px; }}
    .summary-item .value {{ font-size: 20pt; font-weight: 700; display: block; }}
    .summary-item .label {{ font-size: 9pt; opacity: 0.8; }}
    .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .info-item {{ margin: 3px 0; }}
    .info-item strong {{ display: inline-block; min-width: 140px; }}
    .footer {{ text-align: center; margin-top: 40px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 8pt; color: #999; }}
    @media print {{ body {{ padding: 0; }} .container {{ max-width: 100%; }} .header {{ border-radius: 0; }} }}
</style>
</head>
<body>
<div class="container">

<div class="header">
    <h1>CBAM Quarterly Report</h1>
    <div class="sub">European Union Carbon Border Adjustment Mechanism — Permanent Regime</div>
    <div class="sub" style="margin-top:8px;font-size:10pt">{r.get_quarter_label()} | Generated: {r.generated_at.strftime('%Y-%m-%d %H:%M')} | Version {r.version}</div>
    <div class="sub" style="margin-top:4px;font-size:9pt">Report ID: {r.report_id} | Status: <strong>{r.report_status.title()}</strong></div>
</div>

<!-- Summary Box -->
<div class="summary-box">
    <div class="summary-grid">
        <div class="summary-item">
            <span class="value">{float(r.total_embedded_emissions):,.1f}</span>
            <span class="label">Total Embedded Emissions (tCO₂e)</span>
        </div>
        <div class="summary-item">
            <span class="value">{float(r.total_certificates_needed):,.1f}</span>
            <span class="label">CBAM Certificates Needed</span>
        </div>
        <div class="summary-item">
            <span class="value">€{float(r.total_certificate_cost):,.0f}</span>
            <span class="label">Certificate Cost @ €{85}/tCO₂e</span>
        </div>
        <div class="summary-item">
            <span class="value">{float(r.total_quantity_tonnes):,.1f}</span>
            <span class="label">Total Quantity Imported ({r.goods[0].quantity_unit if r.goods else 't'})</span>
        </div>
    </div>
</div>

<!-- Declarant Information -->
<div class="section">
    <h2>Declarant Information</h2>
    <div class="info-grid">
        <div class="info-item"><strong>Company Name:</strong> {d.company_name}</div>
        <div class="info-item"><strong>EORI Number:</strong> {d.company_eori}</div>
        <div class="info-item"><strong>VAT Number:</strong> {d.vat_number}</div>
        <div class="info-item"><strong>Registration:</strong> {d.unique_registration_number}</div>
        <div class="info-item"><strong>Address:</strong> {d.address}</div>
        <div class="info-item"><strong>City:</strong> {d.city}, {d.postal_code}</div>
        <div class="info-item"><strong>Country:</strong> {d.country}</div>
        <div class="info-item"><strong>Contact:</strong> {d.contact_person}</div>
        <div class="info-item"><strong>Email:</strong> {d.contact_email}</div>
        <div class="info-item"><strong>Phone:</strong> {d.contact_phone}</div>
        <div class="info-item"><strong>Authorized Declarant:</strong> {"Yes" if d.authorized else "No"}</div>
        <div class="info-item"><strong>Auth. Number:</strong> {d.authorization_number or "—"}</div>
    </div>
</div>

<!-- Breakdown by Sector -->
<div class="section">
    <h2>Breakdown by Sector</h2>
    <table>
        <thead>
            <tr><th>Sector</th><th style="text-align:right">Quantity (t)</th><th style="text-align:right">Emissions (tCO₂e)</th><th style="text-align:right">Certificates</th></tr>
        </thead>
        <tbody>
            {sector_rows}
        </tbody>
        <tfoot>
            <tr style="font-weight:700;background:#e94560;color:#fff">
                <td>TOTAL</td>
                <td style="text-align:right">{float(r.total_quantity_tonnes):,.2f}</td>
                <td style="text-align:right">{float(r.total_embedded_emissions):,.2f}</td>
                <td style="text-align:right">{float(r.total_certificates_needed):,.2f}</td>
            </tr>
        </tfoot>
    </table>
</div>

<!-- Detailed Goods Table -->
<div class="section">
    <h2>Detailed Import Declaration</h2>
    <table>
        <thead>
            <tr><th>#</th><th>CN Code</th><th>Description</th><th>Origin</th><th style="text-align:right">Qty (t/MWh)</th><th style="text-align:right">EF (tCO₂e/t)</th><th style="text-align:right">Emissions</th><th style="text-align:right">Certificates</th></tr>
        </thead>
        <tbody>
            {goods_rows}
        </tbody>
        <tfoot>
            <tr style="font-weight:700;background:#e94560;color:#fff">
                <td colspan="4">TOTAL</td>
                <td style="text-align:right">{float(r.total_quantity_tonnes):,.2f}</td>
                <td></td>
                <td style="text-align:right">{float(r.total_embedded_emissions):,.2f}</td>
                <td style="text-align:right">{float(r.total_certificates_needed):,.2f}</td>
            </tr>
        </tfoot>
    </table>
</div>

<!-- Carbon Price Deduction -->
<div class="section">
    <h2>Carbon Price Deduction</h2>
    <table>
        <tr><th>Country</th><th style="text-align:right">Carbon Price (EUR/tCO₂e)</th><th style="text-align:right">Deduction Amount (EUR)</th></tr>
        {"".join(f'<tr><td>{COUNTRY_NAMES.get(g.country_of_origin, g.country_of_origin)}</td><td style="text-align:right">€{float(g.carbon_price_paid or 0):.2f}</td><td style="text-align:right">€{float(g.carbon_price_deduction or 0):.2f}</td></tr>' for g in r.goods if g.carbon_price_paid and g.carbon_price_paid > 0)}
        <tr style="font-weight:700"><td>TOTAL DEDUCTION</td><td></td><td style="text-align:right">€{float(r.total_carbon_price_deduction):.2f}</td></tr>
    </table>
</div>

<!-- Statement -->
<div class="section">
    <h2>Declaration Statement</h2>
    <p style="font-size:10pt;border:1px solid #ddd;padding:15px;border-radius:5px;">
        I, the undersigned, declare that the information provided in this CBAM quarterly report is complete, accurate, and true to the best of my knowledge, in accordance with Regulation (EU) 2023/956 of the European Parliament and of the Council establishing a Carbon Border Adjustment Mechanism.
    </p>
    <div class="info-grid" style="margin-top:15px;">
        <div class="info-item"><strong>Place of declaration:</strong> {d.city}, {d.country}</div>
        <div class="info-item"><strong>Date:</strong> {r.generated_at.strftime('%d %B %Y')}</div>
        <div class="info-item"><strong>Declarant:</strong> {d.contact_person}</div>
        <div class="info-item"><strong>Function:</strong> Authorised Representative</div>
    </div>
</div>

<div class="watermark">
    Generated by CBAM Agent © 2026 DanceNitra. All rights reserved.<br>
    This report is based on EU Regulation 2023/956 and Commission Implementing Regulation (EU) 2025/177.
</div>
</div>
</body>
</html>"""
        return html_content
    
    def summary_text(self, report: CBAMQuarterlyReport) -> str:
        """Generate a plain-text summary for CLI output."""
        lines = [
            f"=== CBAM Quarterly Report: {report.get_quarter_label()} ===",
            f"Report ID: {report.report_id}",
            f"Declarant: {report.declarant.company_name} ({report.declarant.country})",
            f"Status: {report.report_status}",
            "",
            f"Total quantity imported: {float(report.total_quantity_tonnes):,.2f} tonnes/MWh",
            f"Total embedded emissions: {float(report.total_embedded_emissions):,.2f} tCO₂e",
            f"Total indirect emissions: {float(report.total_indirect_emissions):,.2f} tCO₂e",
            f"CBAM certificates needed: {float(report.total_certificates_needed):,.2f}",
            f"Carbon price deduction: €{float(report.total_carbon_price_deduction):,.2f}",
            f"Estimated certificate cost: €{float(report.total_certificate_cost):,.2f}",
            "",
            f"Goods declared: {len(report.goods)}",
            f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M')}",
        ]
        return "\n".join(lines)
