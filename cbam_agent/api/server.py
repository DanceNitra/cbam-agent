"""
CBAM Comply — Multi-Declarant API Server
Copyright (c) 2026 DanceNitra. All rights reserved.

FastAPI server for multi-tenant CBAM report generation.
Supports:
- Company registration (declarant profiles)
- CSV/JSON import upload
- Report generation and download
- Multi-user per company
- API key authentication
"""
import json
import os
import uuid
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, EmailStr

# Try to import FastAPI dependencies
try:
    from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Security
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    import uvicorn
except ImportError:
    raise ImportError(
        "FastAPI dependencies not installed. Run:\n"
        "  pip install fastapi uvicorn python-multipart"
    )

from ..engine.engine import CBAMEngine
from ..engine.erp_importer import ERPImporter
from ..data.report_model import DeclarantInfo, CBAMQuarterlyReport

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class CompanyRegistration(BaseModel):
    """Request to register a new CBAM declarant company."""
    company_name: str
    eori: str
    vat_number: str
    registration_number: str = ""
    address: str
    city: str
    postal_code: str
    country: str
    contact_person: str
    contact_email: str
    contact_phone: str


class CompanyResponse(BaseModel):
    """Company registration response."""
    company_id: str
    api_key: str
    company_name: str
    created_at: str


class ImportRow(BaseModel):
    """Single import row in API request."""
    cn_code: str
    description: str = ""
    quantity: float
    country: str
    unit: str = "tonnes"
    actual_emissions: Optional[float] = None
    verified: bool = False


class ReportRequest(BaseModel):
    """Request to generate a CBAM report via API."""
    year: int = 2026
    quarter: int = 1
    goods: List[ImportRow]
    format: str = "html"  # html, json, both


class ReportResponse(BaseModel):
    """Report generation response."""
    report_id: str
    company_name: str
    quarter: str
    total_quantity_tonnes: float
    total_embedded_emissions: float
    total_certificates_needed: float
    total_certificate_cost_eur: float
    total_carbon_price_deduction_eur: float
    goods_count: int
    report_url: str
    json_url: str
    status: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    companies_registered: int

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CBAM Comply API",
    description="Automated EU Carbon Border Adjustment Mechanism (CBAM) quarterly reporting",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Data storage
# ---------------------------------------------------------------------------

STORAGE_DIR = Path(__file__).parent.parent / "data" / "api"
COMPANIES_FILE = STORAGE_DIR / "companies.json"
REPORTS_DIR = STORAGE_DIR / "reports"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_companies() -> Dict:
    """Load registered companies from disk."""
    if COMPANIES_FILE.exists():
        with open(COMPANIES_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_companies(companies: Dict) -> None:
    """Save registered companies to disk."""
    with open(COMPANIES_FILE, 'w') as f:
        json.dump(companies, f, indent=2)


def _get_company_from_api_key(api_key: str) -> Optional[Dict]:
    """Lookup company by API key."""
    companies = _load_companies()
    for cid, company in companies.items():
        if company.get("api_key") == api_key:
            return {"id": cid, **company}
    return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    companies = _load_companies()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        companies_registered=len(companies),
    )


@app.post("/companies/register", response_model=CompanyResponse)
async def register_company(reg: CompanyRegistration):
    """Register a new CBAM declarant company."""
    companies = _load_companies()
    
    # Check for duplicate (by EORI or VAT)
    for cid, company in companies.items():
        if company["eori"] == reg.eori:
            raise HTTPException(status_code=409, detail=f"Company with EORI {reg.eori} already registered (ID: {cid})")
    
    company_id = f"CBAM-{uuid.uuid4().hex[:8].upper()}"
    api_key = f"cbam_{uuid.uuid4().hex}_{uuid.uuid4().hex[:8]}"
    
    companies[company_id] = {
        "company_name": reg.company_name,
        "eori": reg.eori,
        "vat_number": reg.vat_number,
        "registration_number": reg.registration_number,
        "address": reg.address,
        "city": reg.city,
        "postal_code": reg.postal_code,
        "country": reg.country,
        "contact_person": reg.contact_person,
        "contact_email": reg.contact_email,
        "contact_phone": reg.contact_phone,
        "api_key": api_key,
        "created_at": datetime.now().isoformat(),
        "authorized": False,
        "authorization_number": "",
    }
    
    _save_companies(companies)
    
    return CompanyResponse(
        company_id=company_id,
        api_key=api_key,
        company_name=reg.company_name,
        created_at=companies[company_id]["created_at"],
    )


@app.get("/companies/me")
async def get_my_company(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current company details."""
    company = _get_company_from_api_key(credentials.credentials)
    if not company:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {k: v for k, v in company.items() if k != "api_key"}


@app.post("/reports/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Generate a CBAM quarterly report from import data."""
    company = _get_company_from_api_key(credentials.credentials)
    if not company:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Validate quarter
    if request.quarter not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="Quarter must be 1, 2, 3, or 4")
    
    # Create declarant info
    declarant = DeclarantInfo(
        company_name=company["company_name"],
        company_eori=company["eori"],
        vat_number=company["vat_number"],
        unique_registration_number=company.get("registration_number", ""),
        address=company["address"],
        city=company["city"],
        postal_code=company["postal_code"],
        country=company["country"],
        contact_person=company["contact_person"],
        contact_email=company["contact_email"],
        contact_phone=company["contact_phone"],
        authorized=company.get("authorized", False),
        authorization_number=company.get("authorization_number", ""),
    )
    
    # Convert API rows to dict list
    rows = []
    for g in request.goods:
        row = {
            "cn_code": g.cn_code,
            "description": g.description,
            "quantity": g.quantity,
            "country": g.country,
            "unit": g.unit,
        }
        if g.actual_emissions is not None:
            row["actual_emissions"] = g.actual_emissions
        if g.verified:
            row["verified"] = True
        rows.append(row)
    
    # Generate report
    engine = CBAMEngine()
    report = engine.create_report_from_rows(
        rows, declarant, request.year, request.quarter
    )
    
    # Save outputs
    company_dir = REPORTS_DIR / company["id"]
    company_dir.mkdir(parents=True, exist_ok=True)
    
    html_path = company_dir / f"{report.report_id}.html"
    json_path = company_dir / f"{report.report_id}.json"
    
    engine.generate_html_report(report, str(html_path))
    
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
    
    return ReportResponse(
        report_id=report.report_id,
        company_name=declarant.company_name,
        quarter=report.get_quarter_label(),
        total_quantity_tonnes=float(report.total_quantity_tonnes),
        total_embedded_emissions=float(report.total_embedded_emissions),
        total_certificates_needed=float(report.total_certificates_needed),
        total_certificate_cost_eur=float(report.total_certificate_cost),
        total_carbon_price_deduction_eur=float(report.total_carbon_price_deduction),
        goods_count=len(report.goods),
        report_url=f"/reports/download/{company['id']}/{report.report_id}.html",
        json_url=f"/reports/download/{company['id']}/{report.report_id}.json",
        status=report.report_status,
    )


@app.post("/reports/upload")
async def upload_and_generate(
    year: int = Form(2026),
    quarter: int = Form(1),
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Upload a CSV/JSON file and generate a CBAM report."""
    company = _get_company_from_api_key(credentials.credentials)
    if not company:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Save uploaded file
    upload_dir = REPORTS_DIR / company["id"] / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    content = await file.read()
    with open(file_path, 'wb') as f:
        f.write(content)
    
    # Parse and generate
    try:
        importer = ERPImporter()
        rows = importer.load(str(file_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")
    
    declarant = DeclarantInfo(
        company_name=company["company_name"],
        company_eori=company["eori"],
        vat_number=company["vat_number"],
        unique_registration_number=company.get("registration_number", ""),
        address=company["address"],
        city=company["city"],
        postal_code=company["postal_code"],
        country=company["country"],
        contact_person=company["contact_person"],
        contact_email=company["contact_email"],
        contact_phone=company["contact_phone"],
        authorized=company.get("authorized", False),
        authorization_number=company.get("authorization_number", ""),
    )
    
    engine = CBAMEngine()
    report = engine.create_report_from_rows(rows, declarant, year, quarter)
    
    company_dir = REPORTS_DIR / company["id"]
    html_path = company_dir / f"{report.report_id}.html"
    json_path = company_dir / f"{report.report_id}.json"
    
    engine.generate_html_report(report, str(html_path))
    
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
    
    return ReportResponse(
        report_id=report.report_id,
        company_name=declarant.company_name,
        quarter=report.get_quarter_label(),
        total_quantity_tonnes=float(report.total_quantity_tonnes),
        total_embedded_emissions=float(report.total_embedded_emissions),
        total_certificates_needed=float(report.total_certificates_needed),
        total_certificate_cost_eur=float(report.total_certificate_cost),
        total_carbon_price_deduction_eur=float(report.total_carbon_price_deduction),
        goods_count=len(report.goods),
        report_url=f"/reports/download/{company['id']}/{report.report_id}.html",
        json_url=f"/reports/download/{company['id']}/{report.report_id}.json",
        status=report.report_status,
    )


@app.get("/reports/download/{company_id}/{filename}")
async def download_report(company_id: str, filename: str):
    """Download a generated report file."""
    file_path = REPORTS_DIR / company_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(str(file_path), media_type="text/html" if filename.endswith('.html') else "application/json")


@app.get("/reports/list")
async def list_reports(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """List all generated reports for the current company."""
    company = _get_company_from_api_key(credentials.credentials)
    if not company:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    company_dir = REPORTS_DIR / company["id"]
    if not company_dir.exists():
        return {"reports": []}
    
    reports = []
    for f in sorted(company_dir.glob("*.json")):
        if f.name == "companies.json":
            continue
        try:
            with open(f) as jf:
                data = json.load(jf)
            reports.append(data)
        except (json.JSONDecodeError, IOError):
            continue
    
    return {"reports": reports}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    """Run the API server."""
    host = os.environ.get("CBAM_API_HOST", "0.0.0.0")
    port = int(os.environ.get("CBAM_API_PORT", "8080"))
    
    print(f"🚀 CBAM Comply API starting on http://{host}:{port}")
    print(f"   Swagger docs: http://{host}:{port}/docs")
    print(f"   Health check: http://{host}:{port}/health")
    
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
