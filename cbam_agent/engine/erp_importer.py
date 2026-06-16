"""
Enhanced ERP Import Parser

Handles real-world exports from:
- SAP (various formats)
- Oracle ERP
- Customs declaration systems
- Generic CSV with flexible column mapping

Supports auto-detection of file format and column mapping.
"""
import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal, InvalidOperation

from ..data.cn_codes import get_sector_for_cn_code, get_all_cn_codes
from .security import SecurityGuardrails


# Known ERP column name mappings
COLUMN_MAPPINGS: Dict[str, Dict[str, str]] = {
    "standard": {
        "cn_code": ["cn_code", "cncode", "taric", "tariff", "hscode", "hs_code", "hs code", "commodity code", "product code", "code"],
        "quantity": ["quantity", "qty", "net_mass", "netmass", "net_weight", "netweight", "weight", "mass", "volume", "amount", "total_qty", "net weight", "net weight (kg)", "net weight (t)", "gross weight", "gross_weight", "kg", "tonnes", "tons", "mt"],
        "country": ["country", "country_of_origin", "origin", "origin_country", "coo", "country_code", "cntry", "origin_code"],
        "description": ["description", "descr", "desc", "product_name", "product", "goods_description", "item_description", "text"],
        "actual_emissions": ["actual_emissions", "actual_emission", "actual_em", "verified_emissions", "real_emissions", "known_emissions", "supplier_emissions", "ef_verified", "co2_factor"],
        "verified": ["verified", "verified_emissions", "is_verified", "verification_status", "third_party_verified", "verification_yn"],
        "unit": ["unit", "uom", "unit_of_measure", "measure_unit", "quantity_unit", "qty_unit"],
        "value_eur": ["value", "value_eur", "invoice_value", "customs_value", "statistical_value", "amount_eur"],
        "supplier": ["supplier", "vendor", "manufacturer", "producer", "exporter", "supplier_name"],
        "invoice": ["invoice", "invoice_no", "invoice_number", "document_no", "document_number"],
        "shipment_date": ["shipment_date", "date", "import_date", "arrival_date", "declaration_date", "entry_date"],
    }
}


class ERPImporter:
    """Enhanced import parser for ERP/Customs exports."""
    
    def __init__(self):
        self.guardrails = SecurityGuardrails()
    
    def detect_format(self, filepath: str) -> str:
        """Auto-detect file format from content."""
        path = Path(filepath)
        suffix = path.suffix.lower()
        
        if suffix in ('.csv', '.txt', '.tsv'):
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                header = f.read(4096)
            
            # Detect SAP format (often has special structure)
            if any(s in header for s in ['SAP', 'R/3', '/SAP', 'BAPI']):
                return 'sap_csv'
            
            # Detect Oracle format
            if any(s in header for s in ['Oracle', 'R11', 'R12']):
                return 'oracle_csv'
            
            # Detect tab-separated
            if '\t' in header and ',' not in header[:500]:
                return 'tsv'
            
            # Detect semicolon separator (EU locales)
            if ';' in header and ',' not in header[:500]:
                return 'csv_semicolon'
            
            return 'csv'
        
        elif suffix in ('.json', '.jsonl'):
            return 'json'
        
        elif suffix in ('.xls', '.xlsx'):
            return 'excel'
        
        return 'csv'  # default
    
    def load(self, filepath: str, format_hint: Optional[str] = None) -> List[Dict]:
        """Load import data from any supported format."""
        path = Path(filepath)
        self.guardrails.validate_path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        fmt = format_hint or self.detect_format(filepath)
        
        if fmt in ('csv', 'csv_semicolon', 'tsv', 'sap_csv', 'oracle_csv'):
            return self._load_delimited(path, fmt)
        elif fmt == 'json':
            return self._load_json(path)
        else:
            raise ValueError(f"Unsupported format: {fmt}")
    
    def _load_delimited(self, path: Path, fmt: str) -> List[Dict]:
        """Load delimited files with flexible parsing."""
        # Determine delimiter
        if fmt == 'tsv':
            delimiter = '\t'
        elif fmt == 'csv_semicolon':
            delimiter = ';'
        else:
            # Auto-detect delimiter
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                first_line = f.readline()
            if '\t' in first_line:
                delimiter = '\t'
            elif ';' in first_line:
                delimiter = ';'
            else:
                delimiter = ','
        
        # Detect encoding (try UTF-8, fallback to Windows-1250 for SK/CZ)
        encodings = ['utf-8', 'utf-8-sig', 'windows-1250', 'iso-8859-2', 'cp1250']
        
        for enc in encodings:
            try:
                with open(path, 'r', encoding=enc) as f:
                    reader = csv.DictReader(f, delimiter=delimiter)
                    rows = list(reader)
                if rows and len(rows[0]) > 0:
                    break
            except (UnicodeDecodeError, csv.Error):
                continue
        
        # Store original column names for unit detection
        detected_columns = list(rows[0].keys()) if rows else []
        
        # Normalize column headers using mappings
        normalized = []
        for row in rows:
            normalized_row = self._normalize_columns(dict(row))
            normalized.append(normalized_row)
        
        # Post-process: detect kg columns and convert to tonnes
        kg_column_detected = any('kg' in col.lower() for col in detected_columns)
        if kg_column_detected:
            for row in normalized:
                if 'quantity' in row and row['quantity']:
                    try:
                        val = float(str(row['quantity']).replace(',', '.').replace(' ', ''))
                        # If value > 10000 and no 'MWh' unit, assume kg -> convert to tonnes
                        if val > 10000:
                            row['quantity'] = val / 1000.0
                    except (ValueError, TypeError):
                        pass
        
        return [self.guardrails.sanitize_row(r) for r in normalized]
    
    def _load_json(self, path: Path) -> List[Dict]:
        """Load JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            data = data.get('goods', data.get('imports', data.get('items', data.get('data', [data]))))
        
        if not isinstance(data, list):
            data = [data]
        
        return [self._normalize_columns(dict(row)) for row in data]
    
    def _normalize_columns(self, row: Dict) -> Dict:
        """Normalize column names to standard fields using fuzzy matching."""
        normalized: Dict[str, Any] = {}
        
        # Build reverse mapping: lowercase standardized column name -> canonical field
        canonical_map = {}
        for field, aliases in COLUMN_MAPPINGS["standard"].items():
            for alias in aliases:
                canonical_map[alias.lower()] = field
        
        # Also add simple mapping (cn_code -> cn_code)
        for field in COLUMN_MAPPINGS["standard"]:
            canonical_map[field.lower()] = field
        
        for key, value in row.items():
            key_clean = key.strip().lower()
            
            # Try exact match
            if key_clean in canonical_map:
                canonical = canonical_map[key_clean]
                normalized[canonical] = value
                continue
            
            # Try removing spaces/underscores
            key_no_spaces = re.sub(r'[\s_\-\.]+', '', key_clean)
            for alias, canonical in canonical_map.items():
                alias_no_spaces = re.sub(r'[\s_\-\.]+', '', alias.lower())
                if key_no_spaces == alias_no_spaces:
                    normalized[canonical] = value
                    break
            else:
                # Keep original key
                normalized[key_clean] = value
        
        return normalized


class SAPFormatParser:
    """Specialized parser for SAP R/3 exports.
    
    SAP often exports with:
    - Tab-delimited or semicolon
    - Special header rows with metadata
    - Column names in SAP format (MATNR, WERKS, etc.)
    - Date formats like DD.MM.YYYY
    - Decimal comma (EU format)
    """
    
    SAP_FIELD_MAP = {
        'MATNR': 'cn_code',        # Material number (often contains customs code)
        'WERKS': 'plant',
        'MENGE': 'quantity',       # Quantity
        'MEINS': 'unit',           # Unit of measure
        'BUKRS': 'company_code',
        'LIFNR': 'supplier',
        'TCODE': 'cn_code',        # Tariff code
        'TARIF': 'cn_code',        # Tariff number
        'NTGEW': 'quantity',       # Net weight
        'BRGEW': 'quantity',       # Gross weight
        'GEWEI': 'unit',           # Weight unit
        'CUSTOMS_TARIF_NO': 'cn_code',
        'ORIGIN': 'country',
        'ORIGIN_COUNTRY': 'country',
        'HERKL': 'country',        # Country of origin (SAP field)
        'HERKR': 'region',
    }
    
    @classmethod
    def parse_sap_columns(cls, row: Dict) -> Dict:
        """Map SAP field names to standard names."""
        mapped = {}
        for key, value in row.items():
            key_upper = key.strip().upper()
            if key_upper in cls.SAP_FIELD_MAP:
                mapped[cls.SAP_FIELD_MAP[key_upper]] = value
            else:
                mapped[key_upper.lower()] = value
        
        # Handle decimal comma (EU) -> decimal point
        for num_field in ['quantity', 'net_weight', 'gross_weight', 'value']:
            if num_field in mapped and isinstance(mapped[num_field], str):
                mapped[num_field] = mapped[num_field].replace(' ', '').replace(',', '.')
        
        return mapped
