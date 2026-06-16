#!/usr/bin/env python3
"""
CBAM Agent — CLI Entry Point
Copyright (c) 2026 DanceNitra. All rights reserved.

Usage:
    python -m cbam_agent generate report --declarant demo --quarter 2026-1 --input data/imports.csv
    python -m cbam_agent generate report --declarant demo --quarter 2026-1 --input data/imports.json
    python -m cbam_agent list-sectors
    python -m cbam_agent list-cn-codes [sector]
    python -m cbam_agent list-countries
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional

from .engine.engine import CBAMEngine
from .engine.security import SecurityGuardrails
from .data.cn_codes import SECTORS, COUNTRY_NAMES, get_sector_for_cn_code
from .data.report_model import (
    CBAMQuarterlyReport, DeclarantInfo, ImportedGood
)

# Built-in demo declarant profiles
DEMO_DECLARANTS: Dict[str, DeclarantInfo] = {
    "demo": DeclarantInfo(
        company_name="DanceNitra Trading s.r.o.",
        company_eori="SK1234567890EORI",
        vat_number="SK2024123456",
        unique_registration_number="56781234",
        address="Hlavná 123",
        city="Nitra",
        postal_code="949 01",
        country="SK",
        contact_person="Rastislav Drahoš",
        contact_email="rastislav.drahos@drahos.sk",
        contact_phone="+421 905 123 456",
        authorized=True,
        authorization_number="CBAM-AUTH-SK-2026-001",
    ),
    "zse": DeclarantInfo(
        company_name="ZSE Energia, a.s.",
        company_eori="SK2021123456EORI",
        vat_number="SK2020123456",
        unique_registration_number="35823545",
        address="Čulenova 6",
        city="Bratislava",
        postal_code="816 47",
        country="SK",
        contact_person="CSRD Compliance Officer",
        contact_email="compliance@zse.sk",
        contact_phone="+421 2 5900 1111",
        authorized=True,
        authorization_number="CBAM-AUTH-SK-2026-012",
    ),
    "slovnaft": DeclarantInfo(
        company_name="Slovnaft, a.s.",
        company_eori="SK2023123456EORI",
        vat_number="SK2021123456",
        unique_registration_number="00686242",
        address="Vlčie hrdlo 1",
        city="Bratislava",
        postal_code="824 12",
        country="SK",
        contact_person="Head of Customs",
        contact_email="customs@slovnaft.sk",
        contact_phone="+421 2 5070 1111",
        authorized=True,
        authorization_number="CBAM-AUTH-SK-2026-015",
    ),
}

# Built-in demo import data
DEMO_IMPORTS_JSON = {
    "goods": [
        {
            "cn_code": "7601.10.00",
            "description": "Unwrought aluminium not alloyed, primary",
            "quantity": 1500.0,
            "country": "RU",
            "actual_emissions": 2.100,
            "verified": False,
        },
        {
            "cn_code": "7601.20.00",
            "description": "Unwrought aluminium alloys",
            "quantity": 850.0,
            "country": "UA",
            "actual_emissions": 1.750,
            "verified": False,
        },
        {
            "cn_code": "7201.10.00",
            "description": "Non-alloy pig iron",
            "quantity": 3200.0,
            "country": "UA",
            "actual_emissions": 1.500,
            "verified": False,
        },
        {
            "cn_code": "7208.10.00",
            "description": "Flat-rolled iron/steel in coils, hot-rolled",
            "quantity": 2800.0,
            "country": "CN",
            "actual_emissions": 1.800,
            "verified": False,
        },
        {
            "cn_code": "7207.11.00",
            "description": "Semi-finished products of iron, <0.25% carbon",
            "quantity": 1800.0,
            "country": "TR",
            "verified": False,
        },
        {
            "cn_code": "3102.10.10",
            "description": "Urea with >45% nitrogen by weight",
            "quantity": 1200.0,
            "country": "EG",
            "verified": False,
        },
        {
            "cn_code": "3105.20.00",
            "description": "NPK mineral fertilizers",
            "quantity": 900.0,
            "country": "RU",
            "verified": False,
        },
        {
            "cn_code": "2523.10.00",
            "description": "Cement clinkers",
            "quantity": 5000.0,
            "country": "DZ",
            "actual_emissions": 0.950,
            "verified": False,
        },
    ]
}

DEMO_ZSE_IMPORTS_JSON = {
    "goods": [
        {
            "cn_code": "2716.00.00",
            "description": "Electrical energy imported for trading purposes",
            "quantity": 45000.0,
            "unit": "MWh",
            "country": "UA",
            "actual_emissions": 0.380,
            "verified": False,
        },
        {
            "cn_code": "7601.10.00",
            "description": "Unwrought aluminium for distribution network",
            "quantity": 320.0,
            "country": "NO",
            "actual_emissions": 1.500,
            "verified": False,
        },
    ]
}

DEMO_SLOVNAFT_IMPORTS_JSON = {
    "goods": [
        {
            "cn_code": "2716.00.00",
            "description": "Electrical energy for refinery operations",
            "quantity": 28000.0,
            "unit": "MWh",
            "country": "CZ",
            "actual_emissions": 0.420,
            "verified": False,
        },
        {
            "cn_code": "7201.10.00",
            "description": "Non-alloy pig iron for refinery construction",
            "quantity": 450.0,
            "country": "UA",
            "verified": False,
        },
    ]
}


def generate_report(args):
    """Generate a CBAM quarterly report."""
    # Resolve declarant
    if args.declarant in DEMO_DECLARANTS:
        declarant = DEMO_DECLARANTS[args.declarant]
    elif args.declarant.endswith('.json'):
        with open(args.declarant, 'r') as f:
            decl_data = json.load(f)
        declarant = DeclarantInfo(**decl_data)
    else:
        print(f"Error: Unknown declarant '{args.declarant}'", file=sys.stderr)
        print(f"Available: {', '.join(DEMO_DECLARANTS.keys())}", file=sys.stderr)
        sys.exit(1)
    
    # Parse quarter
    try:
        year_str, q_str = args.quarter.split('-')
        year = int(year_str)
        quarter = int(q_str.replace('Q', ''))
        if quarter not in (1, 2, 3, 4):
            raise ValueError
    except (ValueError, IndexError):
        print(f"Error: Invalid quarter format. Use '2026-Q1' or '2026-1'", file=sys.stderr)
        sys.exit(1)
    
    # Initialize engine
    engine = CBAMEngine()
    
    # Load import data
    if args.input:
        rows = engine.load_import_data(args.input)
    else:
        # Use demo data based on declarant
        if args.declarant == "zse":
            data = DEMO_ZSE_IMPORTS_JSON["goods"]
        elif args.declarant == "slovnaft":
            data = DEMO_SLOVNAFT_IMPORTS_JSON["goods"]
        else:
            data = DEMO_IMPORTS_JSON["goods"]
        rows = data
    
    # Create report
    report = engine.create_report_from_rows(rows, declarant, year, quarter)
    
    # Determine output path
    output_dir = args.output or os.path.join('reports', declarant.company_name.replace(' ', '_'))
    report_filename = f"{report.report_id}.html"
    output_path = os.path.join(output_dir, report_filename)
    
    # Generate report
    if args.format == 'html' or args.format == 'auto':
        engine.generate_html_report(report, output_path)
        print(f"✅ CBAM report generated: {output_path}")
    
    # Also save JSON summary
    json_path = output_path.replace('.html', '.json')
    summary = {
        "report_id": report.report_id,
        "declarant": declarant.company_name,
        "quarter": report.get_quarter_label(),
        "total_quantity_tonnes": float(report.total_quantity_tonnes),
        "total_embedded_emissions": float(report.total_embedded_emissions),
        "total_certificates_needed": float(report.total_certificates_needed),
        "total_certificate_cost_eur": float(report.total_certificate_cost),
        "total_carbon_price_deduction_eur": float(report.total_carbon_price_deduction),
        "goods_count": len(report.goods),
        "generated_at": report.generated_at.isoformat(),
        "status": report.report_status,
    }
    with open(json_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✅ JSON summary saved: {json_path}")
    
    # Print summary
    print()
    print(engine.summary_text(report))


def list_sectors(args):
    """List all CBAM sectors."""
    print("CBAM Sectors:\n")
    for key, sector in SECTORS.items():
        codes_count = len(sector.cn_codes)
        print(f"  {key:20s} — {sector.name:15s} ({codes_count} CN codes)")


def list_cn_codes(args):
    """List CN codes, optionally filtered by sector."""
    if args.sector and args.sector in SECTORS:
        sectors = {args.sector: SECTORS[args.sector]}
    else:
        sectors = SECTORS
    
    for key, sector in sectors.items():
        print(f"\n{'='*60}")
        print(f"  {sector.name} ({key})")
        print(f"{'='*60}")
        print(f"  {'CN Code':15s} {'EF (tCO2e/t)':15s} {'Description'}")
        print(f"  {'-'*55}")
        for code, desc in sector.cn_codes.items():
            ef = sector.default_emission_factors.get(code, 0)
            print(f"  {code:15s} {ef:15.4f} {desc}")


def list_countries(args):
    """List countries with carbon prices."""
    from .data.cn_codes import THIRD_COUNTRY_CARBON_PRICES
    
    print(f"\nCountries with Carbon Prices (EUR/tCO₂e):")
    print(f"{'Country':25s} {'Code':6s} {'Price (EUR)':15s}")
    print(f"{'-'*46}")
    for code, price in sorted(THIRD_COUNTRY_CARBON_PRICES.items()):
        name = COUNTRY_NAMES.get(code, '')
        print(f"{name:25s} {code:6s} €{price:<12.2f}" if price > 0 else f"{name:25s} {code:6s} {'—':<15s}")


def _start_server(host: Optional[str] = None, port: Optional[int] = None):
    """Start the CBAM Comply API server."""
    os.environ.setdefault("CBAM_API_HOST", host or "0.0.0.0")
    os.environ.setdefault("CBAM_API_PORT", str(port or 8080))
    from .api.server import main as api_main
    api_main()


def main():
    parser = argparse.ArgumentParser(
        description="CBAM Agent — Carbon Border Adjustment Mechanism Quarterly Reporting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m cbam_agent generate report --declarant demo --quarter 2026-Q1
  python -m cbam_agent generate report --declarant zse --quarter 2026-Q2 --output ./reports
  python -m cbam_agent generate report --declarant demo --quarter 2026-1 --input my_imports.csv
  python -m cbam_agent list-sectors
  python -m cbam_agent list-cn-codes iron_steel
  python -m cbam_agent list-countries
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # generate report subcommand
    gen_parser = subparsers.add_parser("generate", help="Generate CBAM report")
    gen_subparsers = gen_parser.add_subparsers(dest="generate_command")
    
    report_parser = gen_subparsers.add_parser("report", help="Generate quarterly CBAM report")
    report_parser.add_argument("--declarant", "-d", default="demo",
                             help="Declarant profile (demo/zse/slovnaft or path to JSON)")
    report_parser.add_argument("--quarter", "-q", default="2026-Q1",
                             help="Quarter, e.g. 2026-Q1 or 2026-1")
    report_parser.add_argument("--input", "-i", default=None,
                             help="Path to CSV or JSON import data (omit for demo data)")
    report_parser.add_argument("--output", "-o", default=None,
                             help="Output directory (default: ./reports/)")
    report_parser.add_argument("--format", "-f", default="auto",
                             choices=["html", "json", "auto"],
                             help="Output format (default: auto)")
    
    # list subcommands
    sectors_parser = subparsers.add_parser("list-sectors", help="List CBAM sectors")
    sectors_parser.set_defaults(func=list_sectors)
    
    cn_parser = subparsers.add_parser("list-cn-codes", help="List CN codes")
    cn_parser.add_argument("sector", nargs="?", default=None, help="Sector name filter")
    cn_parser.set_defaults(func=list_cn_codes)
    
    countries_parser = subparsers.add_parser("list-countries", help="List countries with carbon prices")
    countries_parser.set_defaults(func=list_countries)
    
    # serve (API server)
    serve_parser = subparsers.add_parser("serve", help="Start the CBAM Comply API server")
    serve_parser.add_argument("--host", default=None, help="Host (default: 0.0.0.0)")
    serve_parser.add_argument("--port", type=int, default=None, help="Port (default: 8080)")
    serve_parser.set_defaults(func=lambda a: _start_server(a.host, a.port))
    
    args = parser.parse_args()
    
    if args.command == "generate" and args.generate_command == "report":
        generate_report(args)
    elif hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
