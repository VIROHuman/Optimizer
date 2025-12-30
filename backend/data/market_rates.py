"""
GLOBAL CONSTRUCTION COST REFERENCE LIBRARY (Q4 2024 / Q1 2025 Estimates)
Sources derived from: Arcadis ICC 2024, Turner & Townsend ICMS 2024.
Base Currency: USD
"""

# --- REGIONAL ANCHORS & TIERS ---

# TIER 1: HIGH COST (North America, Western Europe, Australia)
# Characterized by: Unionized/High labor (> $50/hr), strict safety/environmental regs.
TIER_1_US_EU = {
    'steel_price_usd': 1450.0,  # Domestic protectionism (Buy American/European)
    'cement_price_usd': 165.0,  
    'labor_factor': 5.5,        # Very High Labor Cost
    'logistics_factor': 1.1,
    'description': 'Tier 1: High Labor Cost & Regulation (USA/EU)'
}

# TIER 2: INDUSTRIAL BASE (China, India, Vietnam, Turkey)
# Characterized by: Domestic steel production, low labor cost, massive scale.
TIER_2_INDUSTRIAL = {
    'steel_price_usd': 750.0,   # Domestic production (China/India) is cheap
    'cement_price_usd': 95.0,
    'labor_factor': 1.0,        # Baseline (Cheap)
    'logistics_factor': 0.9,    # Excellent Supply Chain
    'description': 'Tier 2: Industrial/Manufacturing Hubs'
}

# TIER 3: IMPORT DEPENDENT (Sub-Saharan Africa, Remote Islands)
# Characterized by: Low labor cost, but EXPENSIVE materials due to shipping/tariffs.
TIER_3_IMPORT = {
    'steel_price_usd': 1150.0,  # Imported Price + Logistics
    'cement_price_usd': 180.0,  # Heavy transport cost for heavy mats
    'labor_factor': 1.5,        # Low base wage, but often requires expat supervision
    'logistics_factor': 1.4,    # Poor infrastructure premium
    'description': 'Tier 3: Import Dependent / Developing'
}

# TIER 4: OIL ECONOMIES (Middle East / GCC)
# Characterized by: Cheap energy/fuel, imported South Asian labor, subsidized cement.
TIER_4_GULF = {
    'steel_price_usd': 950.0,
    'cement_price_usd': 85.0,   # Subsidized energy = cheap cement
    'labor_factor': 1.8,        # Imported contract labor
    'logistics_factor': 1.0,
    'description': 'Tier 4: GCC / Oil Economies'
}

# --- COUNTRY MAPPING ---

COUNTRY_PROFILES = {
    # --- NORTH AMERICA ---
    'US': TIER_1_US_EU,
    'CA': {**TIER_1_US_EU, 'labor_factor': 5.0}, # Canada
    'MX': {**TIER_2_INDUSTRIAL, 'labor_factor': 1.8}, # Mexico (Nearshoring boom)

    # --- EUROPE ---
    'GB': {**TIER_1_US_EU, 'labor_factor': 4.8, 'steel_price_usd': 1300}, # UK
    'DE': TIER_1_US_EU, # Germany
    'FR': TIER_1_US_EU, # France
    'PL': {**TIER_1_US_EU, 'labor_factor': 2.5}, # Poland (Eastern EU Hub)
    'RU': { # Russia (Sanctions Economy)
        'steel_price_usd': 900.0, 
        'cement_price_usd': 110.0, 
        'labor_factor': 1.4, 
        'logistics_factor': 1.5 # Winter/Distance premium
    },

    # --- ASIA ---
    'CN': TIER_2_INDUSTRIAL, # China (Global Price Floor)
    'IN': {**TIER_2_INDUSTRIAL, 'steel_price_usd': 850.0}, # India
    'VN': TIER_2_INDUSTRIAL, # Vietnam
    'ID': TIER_2_INDUSTRIAL, # Indonesia
    'JP': {**TIER_1_US_EU, 'steel_price_usd': 1200, 'labor_factor': 4.5}, # Japan
    'KR': {**TIER_1_US_EU, 'labor_factor': 3.5}, # South Korea

    # --- MIDDLE EAST ---
    'SA': TIER_4_GULF, # Saudi Arabia
    'AE': TIER_4_GULF, # UAE (Dubai/Abu Dhabi)
    'QA': TIER_4_GULF, # Qatar

    # --- AFRICA ---
    'ZA': {**TIER_3_IMPORT, 'steel_price_usd': 1000.0, 'logistics_factor': 1.1}, # South Africa (Regional Hub)
    'NA': TIER_3_IMPORT, # Namibia
    'NG': {**TIER_3_IMPORT, 'logistics_factor': 1.6}, # Nigeria (High Risk/Logistics)
    'KE': TIER_3_IMPORT, # Kenya
    'EG': {**TIER_2_INDUSTRIAL, 'labor_factor': 0.8}, # Egypt (Cheap Steel/Labor)

    # --- SOUTH AMERICA ---
    'BR': {**TIER_2_INDUSTRIAL, 'labor_factor': 1.4, 'logistics_factor': 1.2}, # Brazil
    'CL': {**TIER_1_US_EU, 'labor_factor': 2.5}, # Chile (Mining economy, higher cost)
    'AR': {**TIER_3_IMPORT, 'logistics_factor': 2.0}, # Argentina (Hyperinflation risk)

    # --- OCEANIA ---
    'AU': {**TIER_1_US_EU, 'labor_factor': 6.0, 'logistics_factor': 1.3}, # Australia (Very High Cost)
    'NZ': {**TIER_1_US_EU, 'logistics_factor': 1.4} # New Zealand
}

def get_rates_for_country(country_code: str):
    """
    Returns the specific rates for a country.
    If country is unknown, auto-detects Tier based on region or defaults to Global Average.
    
    Args:
        country_code: ISO 3166-1 alpha-2 country code (e.g., 'US', 'IN', 'GB')
        
    Returns:
        Dictionary with keys:
        - steel_price_usd: Steel price per tonne in USD
        - cement_price_usd: Cement price per m³ in USD
        - labor_factor: Labor cost multiplier (1.0 = baseline)
        - logistics_factor: Logistics/transport cost multiplier (1.0 = baseline)
        - description: Human-readable description of the tier/profile
    """
    # 1. Direct Match
    if country_code in COUNTRY_PROFILES:
        return COUNTRY_PROFILES[country_code]
    
    # 2. Safe Defaults (If unknown, assume it's an expensive developing nation)
    return {
        'steel_price_usd': 1300.0,
        'cement_price_usd': 150.0,
        'labor_factor': 2.0,
        'logistics_factor': 1.3,
        'description': 'Global Default (Conservative)'
    }

