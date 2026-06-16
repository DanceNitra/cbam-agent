"""
CBAM CN Codes (Combined Nomenclature) per sector.
Source: EU Commission Implementing Regulation (EU) 2025/177
Annex I — List of goods covered by CBAM (permanent regime)
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class CbamSector:
    name: str
    cn_codes: Dict[str, str]  # CN code -> description
    default_emission_factors: Dict[str, float]  # CN code -> tCO2e/t (default)
    unit: str = "tonnes"

# Default emission factors (tCO2e per tonne of product)
# Sources: EU Commission default values, World Bank, OECD
# These are conservative estimates used when actual emissions unknown
SECTORS = {
    "cement": CbamSector(
        name="Cement",
        cn_codes={
            "2523.10.00": "Cement clinkers",
            "2523.21.00": "White Portland cement",
            "2523.29.00": "Other Portland cement",
            "2523.30.00": "Aluminous cement",
            "2523.90.00": "Other hydraulic cements",
            "6810.11.10": "Building blocks and bricks of cement",
            "6810.91.00": "Prefabricated structural components of cement",
        },
        default_emission_factors={
            "2523.10.00": 0.860,
            "2523.21.00": 0.750,
            "2523.29.00": 0.750,
            "2523.30.00": 0.720,
            "2523.90.00": 0.700,
            "6810.11.10": 0.500,
            "6810.91.00": 0.550,
        }
    ),
    "iron_steel": CbamSector(
        name="Iron & Steel",
        cn_codes={
            "7201.10.00": "Non-alloy pig iron",
            "7201.20.00": "Alloy pig iron",
            "7202.11.00": "Ferro-manganese >2% carbon",
            "7202.19.00": "Ferro-manganese other",
            "7202.30.00": "Ferro-silico-manganese",
            "7203.10.00": "Ferrous products from direct reduction",
            "7205.10.00": "Granules of pig iron",
            "7207.11.00": "Semi-finished of iron <0.25% carbon",
            "7207.12.10": "Semi-finished other <0.25% carbon",
            "7207.19.00": "Semi-finished other",
            "7208.10.00": "Flat-rolled in coils, hot-rolled",
            "7209.15.00": "Flat-rolled cold-rolled >=3mm",
            "7210.11.00": "Flat-rolled plated or coated with tin",
            "7213.10.00": "Bars and rods irregular coils",
            "7214.20.00": "Bars and rods of iron or steel",
            "7216.10.00": "U, I, H sections hot-rolled",
            "7219.11.00": "Flat-rolled stainless steel hot-rolled >=4.75mm",
            "7222.11.00": "Bars and rods stainless steel hot-rolled",
            "7301.10.00": "Sheet piling of iron or steel",
            "7302.10.00": "Railway rails of iron or steel",
            "7304.11.00": "Seamless stainless steel pipes",
            "7305.11.00": "Longitudinally submerged arc welded pipes",
            "7312.10.00": "Stranded wire of iron or steel",
            "7318.11.00": "Screw, bolt, nut of iron or steel",
        },
        default_emission_factors={
            "7201.10.00": 1.350,
            "7201.20.00": 1.300,
            "7202.11.00": 0.950,
            "7202.19.00": 0.900,
            "7202.30.00": 0.850,
            "7203.10.00": 1.100,
            "7205.10.00": 1.200,
            "7207.11.00": 1.100,
            "7207.12.10": 1.000,
            "7207.19.00": 0.900,
            "7208.10.00": 1.250,
            "7209.15.00": 1.150,
            "7210.11.00": 1.100,
            "7213.10.00": 1.050,
            "7214.20.00": 1.000,
            "7216.10.00": 1.100,
            "7219.11.00": 1.400,
            "7222.11.00": 1.300,
            "7301.10.00": 1.150,
            "7302.10.00": 1.200,
            "7304.11.00": 1.300,
            "7305.11.00": 1.250,
            "7312.10.00": 1.000,
            "7318.11.00": 0.950,
        }
    ),
    "aluminium": CbamSector(
        name="Aluminium",
        cn_codes={
            "7601.10.00": "Unwrought aluminium not alloyed",
            "7601.20.00": "Unwrought aluminium alloys",
            "7603.10.00": "Powders of aluminium non-lamellar",
            "7603.20.00": "Powders of aluminium lamellar",
            "7604.10.00": "Aluminium bars and rods not alloyed",
            "7604.21.00": "Aluminium hollow profiles",
            "7604.29.00": "Aluminium bars other profiles",
            "7605.11.00": "Aluminium wire non-alloy max 7mm",
            "7605.21.00": "Aluminium wire alloy max 7mm",
            "7606.11.00": "Aluminium plates non-alloy >=6mm",
            "7606.12.00": "Aluminium plates alloy >=6mm",
            "7607.11.00": "Aluminium foil backed <=0.2mm",
            "7607.19.00": "Aluminium foil other",
            "7608.10.00": "Aluminium tubes and pipes non-alloy",
            "7608.20.00": "Aluminium tubes and pipes alloys",
            "7609.00.00": "Aluminium tube/pipe fittings",
            "7610.10.00": "Aluminium structures for buildings",
            "7610.90.00": "Aluminium structures other",
            "7611.00.00": "Aluminium tanks and vats",
            "7612.10.00": "Aluminium collapsible tubular containers",
            "7613.00.00": "Aluminium containers for compressed gas",
            "7614.10.00": "Stranded wire steel core aluminium",
            "7614.90.00": "Stranded wire aluminium other",
            "7616.99.10": "Aluminium articles other",
        },
        default_emission_factors={
            "7601.10.00": 1.800,
            "7601.20.00": 1.650,
            "7603.10.00": 1.900,
            "7603.20.00": 1.850,
            "7604.10.00": 1.700,
            "7604.21.00": 1.650,
            "7604.29.00": 1.600,
            "7605.11.00": 1.750,
            "7605.21.00": 1.650,
            "7606.11.00": 1.700,
            "7606.12.00": 1.600,
            "7607.11.00": 1.700,
            "7607.19.00": 1.650,
            "7608.10.00": 1.700,
            "7608.20.00": 1.600,
            "7609.00.00": 1.650,
            "7610.10.00": 1.500,
            "7610.90.00": 1.500,
            "7611.00.00": 1.550,
            "7612.10.00": 1.600,
            "7613.00.00": 1.600,
            "7614.10.00": 1.700,
            "7614.90.00": 1.650,
            "7616.99.10": 1.500,
        }
    ),
    "fertilizers": CbamSector(
        name="Fertilizers",
        cn_codes={
            "2808.00.00": "Nitric acid",
            "2814.10.00": "Anhydrous ammonia",
            "2814.20.00": "Ammonia in aqueous solution",
            "2834.21.00": "Potassium nitrates",
            "3102.10.10": "Urea >45% nitrogen",
            "3102.10.90": "Urea other",
            "3102.21.00": "Ammonium sulphate",
            "3102.30.00": "Ammonium nitrate",
            "3102.40.00": "Ammonium nitrate with calcium carbonate",
            "3102.50.00": "Sodium nitrate",
            "3102.60.00": "Calcium nitrate",
            "3102.80.00": "Urea and ammonium nitrate mixtures",
            "3102.90.00": "Other nitrogenous fertilizers",
            "3103.11.00": "Superphosphates <35% P2O5",
            "3103.19.00": "Superphosphates other",
            "3103.20.00": "Basic slag",
            "3103.90.00": "Other phosphate fertilizers",
            "3104.20.00": "Potassium chloride",
            "3104.30.00": "Potassium sulphate",
            "3105.10.00": "Mineral/chemical fertilizers in tablets",
            "3105.20.00": "NPK fertilizers",
            "3105.30.00": "Diammonium hydrogenorthophosphate",
            "3105.40.00": "Ammonium dihydrogenorthophosphate",
            "3105.51.00": "Nitrates and phosphates mixtures",
            "3105.59.00": "Other NP mixtures",
            "3105.60.00": "PK fertilizers",
            "3105.90.00": "Other fertilizers",
        },
        default_emission_factors={
            "2808.00.00": 0.350,
            "2814.10.00": 1.600,
            "2814.20.00": 1.000,
            "2834.21.00": 0.650,
            "3102.10.10": 1.800,
            "3102.10.90": 1.700,
            "3102.21.00": 0.900,
            "3102.30.00": 1.350,
            "3102.40.00": 1.000,
            "3102.50.00": 0.550,
            "3102.60.00": 0.700,
            "3102.80.00": 1.500,
            "3102.90.00": 1.200,
            "3103.11.00": 0.300,
            "3103.19.00": 0.250,
            "3103.20.00": 0.200,
            "3103.90.00": 0.250,
            "3104.20.00": 0.200,
            "3104.30.00": 0.250,
            "3105.10.00": 0.800,
            "3105.20.00": 0.900,
            "3105.30.00": 0.700,
            "3105.40.00": 0.650,
            "3105.51.00": 0.750,
            "3105.59.00": 0.800,
            "3105.60.00": 0.400,
            "3105.90.00": 0.700,
        }
    ),
    "electricity": CbamSector(
        name="Electricity",
        cn_codes={
            "2716.00.00": "Electrical energy",
        },
        default_emission_factors={
            "2716.00.00": 0.432,  # tCO2e/MWh (EU average grid)
        },
        unit="MWh"
    ),
    "hydrogen": CbamSector(
        name="Hydrogen",
        cn_codes={
            "2804.10.00": "Hydrogen",
        },
        default_emission_factors={
            "2804.10.00": 9.300,  # tCO2e/t (grey hydrogen from natural gas)
        }
    ),
}

# Third country carbon prices (EUR/tCO2e) — used for deduction calculation
# Source: World Bank Carbon Pricing Dashboard 2025
THIRD_COUNTRY_CARBON_PRICES = {
    "CN": 10.50,   # China National ETS
    "UK": 55.00,   # UK ETS
    "KR": 18.00,   # South Korea ETS
    "JP": 3.50,    # Japan carbon tax
    "CA": 40.00,   # Canada federal floor
    "DE": 0.00,    # Germany — EU ETS, no third-country carbon price
    "FR": 0.00,
    "IT": 0.00,
    "ES": 0.00,
    "PL": 0.00,
    "NL": 0.00,
    "BE": 0.00,
    "US": 0.00,    # No national carbon price
    "IN": 0.00,    # No carbon price
    "RU": 0.00,
    "TR": 0.00,
    "UA": 0.00,
    "BR": 0.00,
    "ZA": 0.00,
    "EG": 0.00,
    "SA": 0.00,
    "AE": 0.00,
    "NG": 0.00,
    "DZ": 0.00,
    "MA": 0.00,
    "TN": 0.00,
}

# EU ETS carbon price forecast (EUR/tCO2e) for CBAM certificate calculation
# Used when converting emissions to certificate value
EU_ETS_PRICE_2026 = 85.00  # EUR/tCO2e (conservative estimate)

# Default emission factors by country for electricity (tCO2e/MWh)
# Sources: EU Commission, IEA, national grid operators
COUNTRY_ELECTRICITY_EMISSION_FACTORS = {
    "CN": 0.550,
    "IN": 0.700,
    "US": 0.380,
    "RU": 0.420,
    "JP": 0.430,
    "KR": 0.460,
    "SA": 0.620,
    "AE": 0.480,
    "ZA": 0.900,
    "TR": 0.450,
    "BR": 0.100,
    "UK": 0.220,
    "NO": 0.015,
    "CH": 0.020,
}

# Country-to-region mapping for administrative purposes
EU_MEMBER_STATES = [
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
]

# Valid ISO country codes for CBAM declarations
COUNTRY_NAMES = {
    "AF": "Afghanistan", "ZA": "South Africa", "DZ": "Algeria",
    "AR": "Argentina", "AU": "Australia", "BD": "Bangladesh",
    "BR": "Brazil", "CA": "Canada", "CL": "Chile",
    "CN": "China", "CO": "Colombia", "EG": "Egypt",
    "ET": "Ethiopia", "GH": "Ghana", "IN": "India",
    "ID": "Indonesia", "IR": "Iran", "IQ": "Iraq",
    "IL": "Israel", "JP": "Japan", "JO": "Jordan",
    "KZ": "Kazakhstan", "KE": "Kenya", "KR": "South Korea",
    "KW": "Kuwait", "LB": "Lebanon", "LY": "Libya",
    "MY": "Malaysia", "MX": "Mexico", "MA": "Morocco",
    "MZ": "Mozambique", "MM": "Myanmar", "NG": "Nigeria",
    "NO": "Norway", "OM": "Oman", "PK": "Pakistan",
    "PE": "Peru", "PH": "Philippines", "QA": "Qatar",
    "RU": "Russia", "SA": "Saudi Arabia", "SG": "Singapore",
    "ZA": "South Africa", "CH": "Switzerland", "SY": "Syria",
    "TW": "Taiwan", "TZ": "Tanzania", "TH": "Thailand",
    "TN": "Tunisia", "TR": "Turkey", "UA": "Ukraine",
    "AE": "United Arab Emirates", "UK": "United Kingdom",
    "US": "United States", "UY": "Uruguay", "UZ": "Uzbekistan",
    "VN": "Vietnam", "YE": "Yemen",
}

def get_all_cn_codes() -> Dict[str, str]:
    """Return all CN codes with their descriptions."""
    codes = {}
    for sector in SECTORS.values():
        codes.update(sector.cn_codes)
    return codes

def get_sector_for_cn_code(cn_code: str) -> Optional[str]:
    """Return the sector key for a given CN code."""
    for sector_key, sector in SECTORS.items():
        if cn_code in sector.cn_codes:
            return sector_key
    return None

def get_default_emission_factor(cn_code: str) -> Optional[float]:
    """Get the default emission factor for a CN code."""
    for sector in SECTORS.values():
        if cn_code in sector.default_emission_factors:
            return sector.default_emission_factors[cn_code]
    return None

def get_carbon_price_in_country(country_code: str) -> float:
    """Get the carbon price paid in a third country (EUR/tCO2e)."""
    return THIRD_COUNTRY_CARBON_PRICES.get(country_code.upper(), 0.0)

def get_electricity_emission_factor(country_code: str) -> float:
    """Get the default grid emission factor for electricity imports."""
    return COUNTRY_ELECTRICITY_EMISSION_FACTORS.get(country_code.upper(), 0.450)
