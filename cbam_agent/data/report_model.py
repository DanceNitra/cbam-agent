"""
CBAM Report Data Model

Represents the quarterly CBAM report structure for the permanent regime (2026+).

A CBAM report contains:
- Declarant info (importer)
- Quarter and year
- List of imported goods with embedded emissions
- Country of origin, CN code, quantity, emission factors
- Carbon price paid in country of origin
- Calculated: total embedded emissions, CBAM certificates needed
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional
from decimal import Decimal

# --- Input Data Structures ---

@dataclass
class ImportedGood:
    """A single line item in a CBAM quarterly report."""
    # Product identification (required first, no defaults)
    cn_code: str                 # 8-digit CN code
    description: str             # Product description
    sector: str                  # cement/iron_steel/aluminium/fertilizers/electricity/hydrogen
    quantity_tonnes: Decimal     # Gross mass in tonnes (for electricity: MWh)
    country_of_origin: str       # ISO 2-letter country code
    
    # Optional fields with defaults
    quantity_unit: str = "tonnes"
    country_name: str = ""       # Human-readable name
    actual_emissions: Optional[Decimal] = None  # tCO2e/t (if known from supplier)
    default_emission_factor: Optional[Decimal] = None  # tCO2e/t (from EU defaults)
    indirect_emissions: Optional[Decimal] = None  # tCO2e/t (scope 2, if known)
    carbon_price_paid: Optional[Decimal] = None  # EUR/tCO2e
    carbon_price_currency: str = "EUR"
    verified: bool = False       # Third-party verified emissions data
    verification_body: str = ""
    
    # Computed fields (all optional with None default)
    total_embedded_emissions: Optional[Decimal] = None  # tCO2e
    total_indirect_emissions: Optional[Decimal] = None  # tCO2e
    certificates_needed: Optional[Decimal] = None       # CBAM certificates
    carbon_price_deduction: Optional[Decimal] = None    # EUR deduction


@dataclass
class DeclarantInfo:
    """Information about the CBAM declarant (importer)."""
    company_name: str
    company_eori: str            # EORI number
    vat_number: str              # VAT number (SK########## format for Slovakia)
    address: str
    city: str
    postal_code: str
    country: str                 # EU Member State (e.g., "SK")
    contact_person: str
    contact_email: str
    contact_phone: str
    unique_registration_number: str = ""  # IČO / Company registration
    authorized: bool = False     # Authorized CBAM declarant status
    authorization_number: str = ""


@dataclass
class CBAMQuarterlyReport:
    """Complete CBAM quarterly emission report."""
    # Required fields first
    declarant: DeclarantInfo
    year: int                    # 2026+
    quarter: int                 # 1, 2, 3, 4
    
    # Optional fields with defaults
    report_id: str = ""          # Auto-generated
    goods: List[ImportedGood] = field(default_factory=list)
    total_quantity_tonnes: Decimal = Decimal("0")
    total_embedded_emissions: Decimal = Decimal("0")
    total_indirect_emissions: Decimal = Decimal("0")
    total_certificates_needed: Decimal = Decimal("0")
    total_carbon_price_deduction: Decimal = Decimal("0")
    total_certificate_cost: Decimal = Decimal("0")
    free_allowances_deducted: Decimal = Decimal("0")  # tCO2e
    generated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "CBAM Agent (DanceNitra)"
    version: str = "1.0.0"
    report_status: str = "draft"  # draft, verified, submitted
    
    def calculate_totals(self) -> None:
        """Calculate all emission totals from goods."""
        eu_ets_price = Decimal("85.00")  # EUR/tCO2e
        total_qty = Decimal("0")
        total_ee = Decimal("0")
        total_ie = Decimal("0")
        total_cert = Decimal("0")
        total_ded = Decimal("0")
        
        for good in self.goods:
            qty = good.quantity_tonnes
            
            # Determine emission factor
            if good.actual_emissions is not None:
                ef = good.actual_emissions
            elif good.default_emission_factor is not None:
                ef = good.default_emission_factor
            else:
                ef = Decimal("0")
            
            # Calculate embedded emissions
            ee = qty * ef
            good.total_embedded_emissions = ee
            
            # Indirect emissions
            ie = qty * (good.indirect_emissions or Decimal("0"))
            good.total_indirect_emissions = ie
            
            # Carbon price deduction
            if good.carbon_price_paid is not None:
                deduction = ee * good.carbon_price_paid
                good.carbon_price_deduction = deduction
            else:
                good.carbon_price_deduction = Decimal("0")
            
            # Certificates needed (total embedded - deduction in EU ETS value)
            net = ee - (good.carbon_price_deduction / eu_ets_price if good.carbon_price_deduction else Decimal("0"))
            good.certificates_needed = max(Decimal("0"), net)
            
            total_qty += qty
            total_ee += ee
            total_ie += ie
            total_cert += good.certificates_needed
            total_ded += (good.carbon_price_deduction or Decimal("0"))
        
        self.total_quantity_tonnes = total_qty
        self.total_embedded_emissions = total_ee.quantize(Decimal("0.001"))
        self.total_indirect_emissions = total_ie.quantize(Decimal("0.001"))
        self.total_certificates_needed = total_cert.quantize(Decimal("0.001"))
        self.total_carbon_price_deduction = total_ded.quantize(Decimal("0.01"))
        self.total_certificate_cost = (total_cert * eu_ets_price).quantize(Decimal("0.01"))
    
    def get_quarter_label(self) -> str:
        """Get human-readable quarter label."""
        labels = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
        return f"{labels.get(self.quarter, 'Q?')} {self.year}"
