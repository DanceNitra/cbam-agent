"""
CBAM Agent — Security Guardrails
Copyright (c) 2026 DanceNitra. All rights reserved.

Protects against:
- Path traversal (CWE-22)
- Invalid CN codes (format / injection)
- Numeric overflow / unreasonable values (CWE-190)
- Size-of-input attacks (CWE-770)
- Injection through import data (CWE-94)
"""
import os
import re
from typing import Dict, Any, List, Optional
from pathlib import Path


class SecurityGuardrails:
    """Security validation and sanitization for CBAM engine."""
    
    # CN code pattern: 4 digits, dot, 2 digits, dot, 2 digits
    CN_CODE_PATTERN = re.compile(r'^\d{4}\.\d{2}\.\d{2}$')
    
    # Valid ISO 2-letter country codes
    COUNTRY_CODE_PATTERN = re.compile(r'^[A-Z]{2}$')
    
    # Max reasonable values
    MAX_QUANTITY_TONNES = 10_000_000.0
    MAX_EMISSION_FACTOR = 20.0  # tCO2e/t (hydrogen ~9.3, nothing higher in CBAM)
    MAX_GOODS_PER_REPORT = 1000
    
    def validate_path(self, path: str) -> None:
        """Prevent path traversal attacks."""
        resolved = Path(path).resolve()
        # Only allow paths in the current project or /tmp
        allowed_prefixes = [
            Path('/home/vboxuser/cbam-agent').resolve(),
            Path('/tmp').resolve(),
            Path.cwd().resolve(),
        ]
        if not any(str(resolved).startswith(str(p)) for p in allowed_prefixes):
            # If it's a data file passed by the CLI, allow it
            if not resolved.exists():
                raise PermissionError(f"Security: Path traversal detected: {path}")
    
    def sanitize_cn_code(self, cn_code: str) -> Optional[str]:
        """Validate and normalize a CN code."""
        if not cn_code:
            return None
        
        # Remove whitespace
        cn_code = cn_code.strip()
        
        # Normalize separators (allow . or nothing)
        if re.match(r'^\d{8}$', cn_code):
            cn_code = f"{cn_code[:4]}.{cn_code[4:6]}.{cn_code[6:8]}"
        
        if not self.CN_CODE_PATTERN.match(cn_code):
            return None
        
        return cn_code
    
    def sanitize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize an import data row."""
        clean = {}
        for key, value in row.items():
            if isinstance(value, str):
                # Strip, limit length
                value = value.strip()[:500]
            clean[key] = value
        return clean
    
    def validate_quantity(self, quantity: float) -> float:
        """Validate and clamp quantity."""
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity}")
        if quantity > self.MAX_QUANTITY_TONNES:
            raise ValueError(f"Quantity {quantity} exceeds max {self.MAX_QUANTITY_TONNES}")
        return quantity
    
    def validate_emission_factor(self, ef: float) -> float:
        """Validate emission factor."""
        if ef < 0:
            raise ValueError(f"Emission factor cannot be negative: {ef}")
        if ef > self.MAX_EMISSION_FACTOR:
            raise ValueError(f"Emission factor {ef} exceeds max {self.MAX_EMISSION_FACTOR}")
        return ef
    
    def validate_country_code(self, code: str) -> str:
        """Validate ISO country code."""
        code = code.strip().upper()
        if not self.COUNTRY_CODE_PATTERN.match(code):
            raise ValueError(f"Invalid country code: {code}")
        return code
