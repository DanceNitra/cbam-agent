# CBAM Comply

**Automated EU Carbon Border Adjustment Mechanism (CBAM) quarterly reporting.**

Generate compliant CBAM emission reports from your import data — automatically calculates embedded emissions, CBAM certificate requirements, and carbon price deductions.

## Why CBAM?

| Key Fact | Value |
|----------|-------|
| **Regulation** | EU Regulation 2023/956 |
| **Permanent regime** | **April 2026** (now!) |
| **Reporting frequency** | **Quarterly** |
| **Sectors covered** | Cement, Iron & Steel, Aluminium, Fertilizers, Electricity, Hydrogen |
| **Companies affected** | ~20,000+ importers in EU |
| **Penalties** | €10–50/tCO₂e underreporting + exclusion from importing |
| **Automation potential** | **75–85%** (formula-driven, highest of all EU regulations) |

## Quick Start

```bash
# Generate demo report (8 sample imports, Q1 2026)
python -m cbam_agent generate report --declarant demo --quarter 2026-Q1

# List available CBAM sectors
python -m cbam_agent list-sectors

# View CN codes for a specific sector
python -m cbam_agent list-cn-codes iron_steel

# Generate with your own data (CSV or JSON)
python -m cbam_agent generate report \
  --declarant zse \
  --quarter 2026-Q1 \
  --input my_imports.csv
```

## Output

- **HTML report** — Professional, print-ready document with declarant info, sector breakdown, detailed goods table, and carbon price deduction
- **JSON summary** — Machine-readable data for further processing
- Reports saved to `./reports/<company_name>/`

## Data Requirements

### Input CSV format

```csv
cn_code,description,quantity,country,actual_emissions,verified
7601.10.00,Unwrought aluminium,1500,RU,2.100,false
7201.10.00,Non-alloy pig iron,3200,UA,1.500,false
```

### Input JSON format

```json
{
  "goods": [
    {
      "cn_code": "7601.10.00",
      "description": "Unwrought aluminium",
      "quantity": 1500,
      "country": "RU",
      "actual_emissions": 2.100,
      "verified": false
    }
  ]
}
```

### Supported fields

| Field | Required | Description |
|-------|----------|-------------|
| `cn_code` | ✅ | 8-digit CN code (e.g. `7601.10.00`) |
| `quantity` | ✅ | Mass in tonnes (MWh for electricity) |
| `country` | ✅ | ISO 2-letter country code |
| `description` | ❌ | Product description (auto-filled from CN code) |
| `actual_emissions` | ❌ | Verified emissions factor (tCO₂e/t). If omitted, uses EU default values |
| `verified` | ❌ | Whether emissions are third-party verified |
| `unit` | ❌ | Default: "tonnes", use "MWh" for electricity |

## Architecture

```
cbam-agent/
├── cbam_agent/
│   ├── data/
│   │   ├── cn_codes.py          # CBAM CN codes, emission factors, country data
│   │   └── report_model.py      # Data models (ImportedGood, DeclarantInfo, CBAMQuarterlyReport)
│   ├── engine/
│   │   ├── engine.py            # Core report generation engine
│   │   └── security.py          # Security guardrails (path traversal, injection prevention)
│   └── __main__.py              # CLI entry point
├── clients/
│   └── demo/                    # Demo client profiles
├── reports/                     # Generated reports
├── site/                        # Landing page / marketing
└── README.md
```

## Built-in Declarants

| Profile | Company | Sector |
|---------|---------|--------|
| `demo` | DanceNitra Trading s.r.o. | General trading (SK) |
| `zse` | ZSE Energia, a.s. | Energy (SK) |
| `slovnaft` | Slovnaft, a.s. | Refinery (SK) |

## License

**All Rights Reserved.** Proprietary software — Copyright (c) 2026 DanceNitra.

For licensing inquiries: **contact@dancenitra.sk**
