"""
Cost Engine Module.

This module calculates the total cost of a transmission tower design.

CRITICAL PRINCIPLES:
- Computes cost ONLY for safe designs
- Has NO safety logic
- Does NOT validate designs
- Pure cost calculation function
- PER-TOWER cost only (not per-circuit km)

Cost components:
- Steel (tower structure) - regional rates from market_rates.py
- Foundation (concrete + excavation) - 4 footings per tower
- Transport & Erection - proportional to steel cost
- Regional adjustment factor from market_rates.py

THIS IS A DECISION-SUPPORT COST MODEL, NOT A CONTRACT BOQ.
"""

from typing import Tuple, Optional
from data_models import TowerDesign, OptimizationInputs, TerrainType, SoilCategory
from backend.data.market_rates import get_rates_for_country
import logging
import os

# Get logger - will use root logger configuration from api.py
logger = logging.getLogger(__name__)
# Ensure logger level is at least INFO to show cost messages
# CRITICAL: Set to INFO so error messages are visible
logger.setLevel(logging.INFO)


# ============================================================================
# REGIONAL STEEL RATES (USD per tonne, fabricated steel)
# ============================================================================

REGIONAL_STEEL_RATES = {
    "india": 1400.0,        # Midpoint of $1,200 - $1,600
    "europe": 2100.0,       # Midpoint of $1,800 - $2,400
    "usa": 2400.0,          # Midpoint of $2,000 - $2,800
    "australia": 2600.0,    # Midpoint of $2,200 - $3,000
    "africa": 1850.0,       # Midpoint of $1,500 - $2,200
    "middle_east": 1950.0,  # Midpoint of $1,600 - $2,300
    "default": 2000.0,      # Default if region not found
}


# ============================================================================
# REGIONAL COST MULTIPLIERS BY CATEGORY
# ============================================================================

# Category-specific regional multipliers
# Replaces single blanket regional factor

REGIONAL_MULTIPLIERS = {
    "india": {
        "steel": 0.90,           # Lower steel cost
        "materials": 0.80,       # Lower concrete/materials cost
        "labor": 0.70,           # Much lower labor cost
        "access": 0.85,          # Lower access/logistics cost
    },
    "europe": {
        "steel": 1.05,           # Slightly higher steel cost
        "materials": 1.10,       # Higher materials cost
        "labor": 1.50,           # Much higher labor cost
        "access": 1.20,          # Higher access/logistics cost
    },
    "usa": {
        "steel": 1.10,           # Higher steel cost
        "materials": 1.15,       # Higher materials cost
        "labor": 1.60,           # Very high labor cost
        "access": 1.25,          # Higher access/logistics cost
    },
    "australia": {
        "steel": 1.15,           # Higher steel cost
        "materials": 1.20,       # Higher materials cost
        "labor": 1.70,           # Very high labor cost
        "access": 1.40,          # High access/logistics (remote)
    },
    "africa": {
        "steel": 0.95,           # Moderate steel cost
        "materials": 0.90,       # Lower materials cost
        "labor": 0.75,           # Lower labor cost
        "access": 1.10,          # Higher access/logistics (remote)
    },
    "middle_east": {
        "steel": 1.00,           # Moderate steel cost
        "materials": 0.95,       # Moderate materials cost
        "labor": 0.85,           # Lower labor cost
        "access": 1.15,          # Higher access/logistics (desert)
    },
    "default": {
        "steel": 1.00,
        "materials": 1.00,
        "labor": 1.00,
        "access": 1.00,
    },
}


# ============================================================================
# REGIONAL LAND / RIGHT-OF-WAY RATES (USD per m²)
# ============================================================================

REGIONAL_LAND_RATES = {
    "india": 50.0,           # USD/m² (rural to urban average)
    "europe": 200.0,        # USD/m² (dense population, high land value)
    "usa": 150.0,           # USD/m² (moderate to high)
    "australia": 80.0,      # USD/m² (mostly rural, some urban)
    "africa": 30.0,         # USD/m² (mostly rural)
    "middle_east": 100.0,   # USD/m² (desert/rural, some urban)
    "default": 100.0,       # Default if region not found
}


# ============================================================================
# ROW MODE CONFIGURATION
# Controls corridor width and compensation multiplier
ROW_MODE_CONFIG = {
    "government_corridor": {"width_m": 35, "multiplier": 0.2},
    "rural_private": {"width_m": 45, "multiplier": 0.6},
    "urban_private": {"width_m": 60, "multiplier": 1.0},
    "mixed": {"width_m": 50, "multiplier": 0.8},
}

# REGIONAL ROW CORRIDOR WIDTHS (meters) - Base widths, modified by row_mode
# ============================================================================

REGIONAL_CORRIDOR_WIDTHS = {
    "india": 50.0,          # m (rural to moderate density)
    "europe": 60.0,         # m (dense population, wider corridor)
    "usa": 55.0,            # m (moderate density)
    "australia": 50.0,      # m (mostly rural)
    "africa": 45.0,         # m (mostly rural, narrower corridor)
    "middle_east": 50.0,    # m (desert/rural)
    "default": 50.0,        # Default if region not found
}


# ============================================================================
# BASE UNIT RATES (region-agnostic)
# ============================================================================

CONCRETE_RATE_PER_M3 = 160.0  # USD/m³ (midpoint of $120 - $200)
EXCAVATION_RATE_PER_M3 = 60.0  # USD/m³ (midpoint of $40 - $80)


# ============================================================================
# SOIL ADJUSTMENT FACTORS (for foundation cost)
# ============================================================================

SOIL_FACTORS = {
    SoilCategory.SOFT: 1.30,
    SoilCategory.MEDIUM: 1.00,
    SoilCategory.HARD: 0.85,
    SoilCategory.ROCK: 0.85,  # Same as hard
}


# ============================================================================
# TERRAIN MULTIPLIERS (for transport & erection)
# ============================================================================

TERRAIN_MULTIPLIERS = {
    TerrainType.FLAT: 1.00,
    TerrainType.ROLLING: 1.15,
    TerrainType.MOUNTAINOUS: 1.30,  # "Hilly" mapped to mountainous
    TerrainType.DESERT: 1.20,
}


def _get_region_from_location(project_location: str) -> str:
    """
    Map project location to cost region (for backward compatibility with land rates).
    
    Args:
        project_location: Country/region name
        
    Returns:
        Region key for cost lookup
    """
    location_lower = project_location.lower().strip()
    
    # India
    if "india" in location_lower or "indian" in location_lower:
        return "india"
    
    # Europe
    europe_keywords = [
        "germany", "france", "italy", "spain", "uk", "united kingdom",
        "netherlands", "belgium", "poland", "europe", "european union", "eu"
    ]
    if any(keyword in location_lower for keyword in europe_keywords):
        return "europe"
    
    # USA / North America
    usa_keywords = [
        "usa", "united states", "united states of america", "canada", "mexico", "north america"
    ]
    if any(keyword in location_lower for keyword in usa_keywords):
        return "usa"
    
    # Australia
    if "australia" in location_lower or "australasia" in location_lower or "new zealand" in location_lower:
        return "australia"
    
    # Middle East
    middle_east_keywords = [
        "uae", "united arab emirates", "saudi arabia", "qatar", "kuwait",
        "bahrain", "oman", "middle east"
    ]
    if any(keyword in location_lower for keyword in middle_east_keywords):
        return "middle_east"
    
    # Africa
    africa_keywords = [
        "south africa", "egypt", "nigeria", "kenya", "africa"
    ]
    if any(keyword in location_lower for keyword in africa_keywords):
        return "africa"
    
    # Default
    return "default"


def _get_country_code_from_location(project_location: str) -> str:
    """
    Extract ISO 3166-1 alpha-2 country code from project location string.
    
    Maps common location names to country codes for market_rates lookup.
    
    Args:
        project_location: Country/region name (e.g., "India", "United States", "UK")
        
    Returns:
        ISO 2-letter country code (e.g., "IN", "US", "GB") or "IN" as default
    """
    location_lower = project_location.lower().strip()
    
    # Country code mappings (common names to ISO codes)
    country_mappings = {
        # India
        "india": "IN", "indian": "IN",
        # USA
        "usa": "US", "united states": "US", "united states of america": "US", "america": "US",
        # Canada
        "canada": "CA",
        # Mexico
        "mexico": "MX",
        # UK
        "uk": "GB", "united kingdom": "GB", "britain": "GB", "england": "GB",
        # Europe
        "germany": "DE", "france": "FR", "italy": "IT", "spain": "ES",
        "netherlands": "NL", "belgium": "BE", "poland": "PL", "romania": "RO",
        # Middle East
        "uae": "AE", "united arab emirates": "AE", "dubai": "AE", "abu dhabi": "AE",
        "saudi arabia": "SA", "qatar": "QA", "kuwait": "KW", "bahrain": "BH", "oman": "OM",
        # Asia
        "china": "CN", "japan": "JP", "south korea": "KR", "korea": "KR",
        "vietnam": "VN", "indonesia": "ID", "thailand": "TH", "philippines": "PH",
        "singapore": "SG", "malaysia": "MY",
        # Africa
        "south africa": "ZA", "egypt": "EG", "nigeria": "NG", "kenya": "KE",
        # Australia / Oceania
        "australia": "AU", "new zealand": "NZ",
        # South America
        "brazil": "BR", "argentina": "AR", "chile": "CL",
        # Russia
        "russia": "RU", "russian federation": "RU",
    }
    
    # Direct match
    if location_lower in country_mappings:
        return country_mappings[location_lower]
    
    # Partial match (check if any keyword is in the location string)
    for keyword, code in country_mappings.items():
        if keyword in location_lower:
            return code
    
    # Default to India if unknown
    logger.warning(f"Unknown project location '{project_location}', defaulting to India (IN)")
    return "IN"


def calculate_cost(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> float:
    """
    Calculate total cost of a tower design (PER-TOWER).
    
    This function assumes the design is SAFE (has passed codal checks).
    It does NOT perform any safety validation.
    
    Args:
        design: TowerDesign to cost
        inputs: OptimizationInputs containing project context
        
    Returns:
        Total cost in USD (per single tower)
        
    Note:
        This function is deterministic and has no side effects.
        It does NOT modify the design or inputs.
    """
    # Get market rates for country
    country_code = _get_country_code_from_location(inputs.project_location)
    rates = get_rates_for_country(country_code)
    
    # CRITICAL: Validate steel_price_usd is per TONNE, not per kg
    # Market rates should be $750-1500 per TONNE (not per kg)
    steel_price_usd = rates['steel_price_usd']
    if steel_price_usd < 100.0 or steel_price_usd > 5000.0:
        logger.error(
            f"CRITICAL: steel_price_usd={steel_price_usd} is outside reasonable range ($100-5000/tonne). "
            f"This suggests a unit error (should be per TONNE, not per kg). Country: {country_code}"
        )
        raise ValueError(
            f"Invalid steel_price_usd: ${steel_price_usd}/tonne. "
            f"Expected $100-5000/tonne. Check if market_rates.py has correct units."
        )
    
    # Pricing logs removed to reduce log clutter - keep other logs
    
    # Component 1: Steel cost (using market rates)
    # CRITICAL: steel_price_usd is per TONNE, weight will be in TONNES
    steel_cost_base = _calculate_steel_cost(design, inputs, steel_price_usd)
    steel_cost = steel_cost_base  # Already includes market rate
    
    # Component 2: Foundation materials cost (using market rates)
    # Use concrete_price_usd if available, otherwise cement_price_usd, with fallback
    concrete_price = rates.get('concrete_price_usd') or rates.get('cement_price_usd') or 120.0
    foundation_cost_base = _calculate_foundation_cost(design, inputs, concrete_price)
    foundation_cost = foundation_cost_base  # Already includes market rate
    
    # Component 3: Transport & Erection cost (using market rates)
    erection_cost_base = _calculate_erection_cost(steel_cost_base, inputs)  # Use base steel cost
    # Apply labor and logistics factors from market rates
    erection_cost = erection_cost_base * rates['labor_factor'] * rates['logistics_factor']
    
    # Component 4: Land / Right-of-Way cost
    land_cost = _calculate_land_cost(design, inputs)
    
    # Total per-tower cost (land cost is separate, not multiplied)
    total_cost = steel_cost + foundation_cost + erection_cost + land_cost
    
    return total_cost


def calculate_cost_with_breakdown(
    design: TowerDesign,
    inputs: OptimizationInputs,
    geo_context: Optional[dict] = None
) -> Tuple[float, dict]:
    """
    Calculate total cost with detailed breakdown.
    
    Args:
        design: TowerDesign to cost
        inputs: OptimizationInputs containing project context
        geo_context: Optional geographic context dict with country_name and state
        
    Returns:
        Tuple of (total_cost, breakdown_dict)
        breakdown_dict contains:
        - steel_cost
        - foundation_cost
        - erection_cost
        - regional_factor
        - base_cost (before regional factor)
        - total_cost
        - region
    """
    # Try to use MarketOracle if geo_context is available and GROQ_API_KEY is set
    rates = None
    market_source = "static"
    
    if geo_context and os.getenv("GROQ_API_KEY"):
        try:
            from backend.services.market_oracle import get_rates
            country = geo_context.get("country_name") or inputs.project_location
            region = geo_context.get("state")
            rates = get_rates(country, region)
            market_source = rates.get("source", "groq")
            logger.info(f"CostEngine: Using MarketOracle rates for {country} ({region or 'no region'})")
        except Exception as e:
            logger.warning(f"CostEngine: MarketOracle failed, falling back to static rates: {e}")
            rates = None
    
    # Fallback to static rates if MarketOracle not available or failed
    if rates is None:
        country_code = _get_country_code_from_location(inputs.project_location)
        static_rates = get_rates_for_country(country_code)
        # Convert static rates format to match MarketOracle format
        cement_price = static_rates.get('cement_price_usd', 120.0)
        rates = {
            'steel_price_usd': static_rates['steel_price_usd'],
            'cement_price_usd': cement_price,
            'concrete_price_usd': cement_price,  # Use same value for both
            'labor_factor': static_rates['labor_factor'],
            'logistics_factor': static_rates['logistics_factor'],
            'currency_symbol': '$',
            'currency_code': 'USD',
            'market_note': static_rates.get('description', 'Static market rates'),
            'source': 'static'
        }
        market_source = "static"
    
    # ---------------------------------------------------------
    # 1. CALCULATE BASE COSTS (IN USD)
    # ---------------------------------------------------------
    
    # Get base USD price (MarketOracle should return 'steel_price_usd')
    steel_price_usd = rates['steel_price_usd']
    
    # Validate Units (Keep your existing safety check)
    if steel_price_usd < 100.0:
        logger.warning(f"Price ${steel_price_usd} too low. Converting to tonne.")
        steel_price_usd *= 1000.0

    # Calculate Components in USD
    steel_cost_usd = _calculate_steel_cost(design, inputs, steel_price_usd)
    
    # Apply AI-detected Design Stringency Factor (Neuro-Symbolic Architecture)
    # This factor accounts for local standards that require heavier/safer structures
    design_stringency_factor = rates.get('design_stringency_factor', 1.0)
    if design_stringency_factor != 1.0:
        governing_standard_name = rates.get('governing_standard', 'Unknown')
        logger.info(
            f"[NEURO-SYMBOLIC] AI applied Design Stringency: {design_stringency_factor:.2f}x "
            f"for {governing_standard_name} standard. "
            f"Base steel cost: ${steel_cost_usd:.2f} -> Adjusted: ${steel_cost_usd * design_stringency_factor:.2f}"
        )
        steel_cost_usd = steel_cost_usd * design_stringency_factor
    
    concrete_price_usd = rates.get('concrete_price_usd', rates.get('cement_price_usd', 120.0))
    foundation_cost_usd = _calculate_foundation_cost(design, inputs, concrete_price_usd)
    
    erection_cost_base = _calculate_erection_cost(steel_cost_usd, inputs)
    erection_cost_usd = erection_cost_base * rates['labor_factor'] * rates['logistics_factor']
    
    land_cost_usd = _calculate_land_cost(design, inputs)
    
    total_cost_usd = steel_cost_usd + foundation_cost_usd + erection_cost_usd + land_cost_usd

    # ---------------------------------------------------------
    # 2. APPLY CURRENCY CONVERSION (THE MISSING LINK)
    # ---------------------------------------------------------
    
    # Check if we need to convert (e.g. if symbol is ₹ but math was USD)
    target_currency = rates.get('currency_code', 'USD')
    target_symbol = rates.get('currency_symbol', '$')
    exchange_rate = 1.0
    
    if target_currency != 'USD':
        # If MarketOracle provided a rate, use it. 
        # If not, use a hardcoded fallback for the demo to ensure it works.
        if 'exchange_rate' in rates:
            exchange_rate = rates['exchange_rate']
        elif target_currency == 'INR':
            exchange_rate = 85.0  # Emergency fallback
        elif target_currency == 'EUR':
            exchange_rate = 0.92
        else:
            # Try to fetch real time or default to 1.0
            try:
                from backend.services.market_oracle import get_real_exchange_rate
                exchange_rate = get_real_exchange_rate(target_currency)
            except:
                exchange_rate = 1.0

    # Apply Conversion
    final_steel_cost = steel_cost_usd * exchange_rate
    final_foundation_cost = foundation_cost_usd * exchange_rate
    final_erection_cost = erection_cost_usd * exchange_rate
    final_land_cost = land_cost_usd * exchange_rate
    final_total_cost = total_cost_usd * exchange_rate
    
    # Build market_rates dict with all available fields (including local currency prices from MarketOracle)
    market_rates_dict = {
        "steel_price_usd": steel_price_usd,
        "cement_price_usd": concrete_price_usd,
        "concrete_price_usd": concrete_price_usd,
        "labor_factor": rates['labor_factor'],
        "logistics_factor": rates['logistics_factor'],
        "description": rates.get('market_note', rates.get('description', 'Market rates')),
        "market_source": market_source,  # Add market_source for frontend badge display
    }
    
    # Add local currency prices if available (from MarketOracle)
    if 'steel_price_local_per_tonne' in rates:
        market_rates_dict['steel_price_local_per_tonne'] = rates['steel_price_local_per_tonne']
    if 'steel_price_local_per_kg' in rates:
        market_rates_dict['steel_price_local_per_kg'] = rates['steel_price_local_per_kg']
    if 'concrete_price_local_per_m3' in rates:
        market_rates_dict['concrete_price_local_per_m3'] = rates['concrete_price_local_per_m3']
    
    # Add currency metadata
    if 'currency_symbol' in rates:
        market_rates_dict['currency_symbol'] = rates['currency_symbol']
    if 'currency_code' in rates:
        market_rates_dict['currency_code'] = rates['currency_code']
    if 'exchange_rate' in rates:
        market_rates_dict['exchange_rate'] = rates['exchange_rate']
    
    # Add AI-detected governing standard and stringency factor (Neuro-Symbolic Architecture)
    if 'governing_standard' in rates:
        market_rates_dict['governing_standard'] = rates['governing_standard']
    if 'design_stringency_factor' in rates:
        market_rates_dict['design_stringency_factor'] = rates['design_stringency_factor']
    
    # Add market_note if available (for frontend display)
    if 'market_note' in rates:
        market_rates_dict['market_note'] = rates['market_note']
    
    # ---------------------------------------------------------
    # 3. BUILD RESPONSE
    # ---------------------------------------------------------
    
    breakdown = {
        # Return LOCAL CURRENCY values
        "steel_cost": final_steel_cost,
        "foundation_cost": final_foundation_cost,
        "erection_cost": final_erection_cost,
        "land_cost": final_land_cost,
        "total_cost": final_total_cost,
        
        # Metadata
        "currency_code": target_currency,
        "currency_symbol": target_symbol,
        "exchange_rate_used": exchange_rate,
        "market_source": market_source,
        "market_note": rates.get('market_note', rates.get('description', 'Market rates')),
        
        # Keep raw USD data for debugging
        "raw_usd_cost": total_cost_usd,
        "country_code": _get_country_code_from_location(inputs.project_location) if rates.get('source') == 'static' else None,
        
        # Market rates for frontend display
        "market_rates": market_rates_dict,
    }
    
    # Use currency code instead of symbol to avoid Unicode encoding errors in Windows console
    logger.info(f"[COST] Calculated: ${total_cost_usd:.2f} USD -> {target_currency} {final_total_cost:.2f} (Rate: {exchange_rate})")
    
    return final_total_cost, breakdown


def _calculate_steel_cost(
    design: TowerDesign,
    inputs: OptimizationInputs,
    steel_price_usd: float
) -> float:
    """
    Calculate steel cost for tower structure.
    
    Uses lattice tower approximation:
    steel_weight_tonnes = k × tower_height × base_width
    
    Where k = 0.035 (lattice factor)
    
    CRITICAL: Returns cost in USD. Currency conversion happens at response layer.
    
    Args:
        design: TowerDesign
        inputs: OptimizationInputs
        steel_price_usd: Steel price per tonne in USD (from market_rates)
        
    Returns:
        Steel cost in USD (raw number, no currency symbol)
    """
    # Lattice factor (empirical, range 0.08 - 0.12)
    k = 0.035
    
    # Tower type multiplier
    type_multiplier = {
        "suspension": 1.0,
        "angle": 1.5,
        "tension": 1.2,
        "dead_end": 2.5,
    }
    multiplier = type_multiplier.get(design.tower_type.value, 1.0)
    
    # Base steel weight in TONNES (not kg)
    steel_weight_tonnes = k * design.tower_height * design.base_width * multiplier
    
    # Ice load coupling: When ice load is enabled, increase steel demand
    # Ice loading increases vertical forces, requiring stronger cross-arms and members
    if inputs.include_ice_load:
        # Conservative multiplier: ice increases vertical load by ~30-50%
        # This propagates into cross-arm demand, vertical reactions, and member forces
        ice_multiplier = 1.35  # 35% increase in steel weight for ice loading
        steel_weight_tonnes *= ice_multiplier
    
    # CRITICAL: Formula is steel_cost = (weight_tonnes) * (price_per_tonne)
    # This ensures correct unit conversion: tonnes × USD/tonne = USD
    # 
    # EXAMPLE: 6.86 tonnes × $850/tonne = $5,831 USD
    #          $5,831 USD × 83 INR/USD = ₹483,973 INR
    #
    # CRITICAL FIX: Validate price is reasonable before calculation
    # Market rates should be $750-1500 per TONNE for most countries
    if steel_price_usd < 100.0:
        # Price is suspiciously low - might be per kg instead of per tonne
        # Convert: if price is $0.85/kg, multiply by 1000 to get $850/tonne
        corrected_price = steel_price_usd * 1000.0
        logger.warning(
            f"steel_price_usd={steel_price_usd} is too low (likely per kg). "
            f"Correcting to {corrected_price}/tonne."
        )
        steel_price_usd = corrected_price
    
    steel_cost_usd = steel_weight_tonnes * steel_price_usd
    
    # CRITICAL DEBUG: Log the calculation
    logger.info(
        f"[STEEL_COST_DEBUG] Calculation: {steel_weight_tonnes:.3f} tonnes × ${steel_price_usd:.2f}/tonne = ${steel_cost_usd:.2f} USD"
    )
    
    # CRITICAL: Final validation - cost must be reasonable
    # For 6.86 tonnes at $850/tonne, minimum cost should be ~$5,000 USD
    if steel_cost_usd < steel_weight_tonnes * 100.0:
        # Cost is impossibly low - this indicates a calculation error
        expected_min = steel_weight_tonnes * 100.0
        logger.error(
            f"CRITICAL: Calculated steel cost ${steel_cost_usd:.2f} is too low! "
            f"Weight: {steel_weight_tonnes:.2f} tonnes, Price: ${steel_price_usd}/tonne, "
            f"Expected minimum: ${expected_min:.2f} USD. "
            f"This indicates a unit conversion error."
        )
        # Force correct calculation as fallback
        steel_cost_usd = steel_weight_tonnes * steel_price_usd
        if steel_cost_usd < expected_min:
            raise ValueError(
                f"Steel cost calculation failed: ${steel_cost_usd:.2f} USD is unreasonably low. "
                f"Check if steel_price_usd (${steel_price_usd}) is per tonne, not per kg."
            )
    
    # CRITICAL VALIDATION: Sanity check that cost is reasonable
    # For a 6-tonne tower at $850/tonne, we expect ~$5,100 USD minimum
    # If cost is < $100 USD, something is severely wrong (likely unit conversion error)
    if steel_cost_usd <= 0:
        logger.error(f"Invalid steel cost: {steel_cost_usd} USD for {steel_weight_tonnes:.2f} tonnes at ${steel_price_usd}/tonne")
        raise ValueError(f"Steel cost calculation error: {steel_cost_usd} USD")
    
    # Additional sanity check: cost should be at least $100 per tonne
    if steel_cost_usd < steel_weight_tonnes * 100.0:
        logger.error(
            f"CRITICAL: Steel cost too low! {steel_cost_usd:.2f} USD for {steel_weight_tonnes:.2f} tonnes "
            f"at ${steel_price_usd}/tonne. Expected minimum: ${steel_weight_tonnes * 100.0:.2f} USD. "
            f"This suggests a unit conversion error (kg vs tonnes)."
        )
        raise ValueError(
            f"Steel cost calculation error: {steel_cost_usd:.2f} USD is unreasonably low. "
            f"Check if steel_price_usd is per tonne (expected ${steel_price_usd}/tonne) or if weight is in kg instead of tonnes."
        )
    
    
    return steel_cost_usd


def _calculate_foundation_cost(
    design: TowerDesign,
    inputs: OptimizationInputs,
    cement_price_usd: float
) -> float:
    """
    Calculate foundation cost (concrete + excavation).
    
    Tower has 4 individual leg footings.
    
    Args:
        design: TowerDesign
        inputs: OptimizationInputs
        cement_price_usd: Cement price per m³ in USD (from market_rates)
        
    Returns:
        Foundation cost in USD
    """
    # Single footing volume
    single_footing_volume = (
        design.footing_length *
        design.footing_width *
        design.footing_depth
    )
    
    # Total concrete volume (4 footings)
    total_concrete_volume = 4.0 * single_footing_volume
    
    # Concrete cost - use cement_price_usd directly (per m³)
    # Updated to use realistic global average: $120/m³ (user requirement)
    # cement_price_usd from market_rates is already per m³
    concrete_cost = total_concrete_volume * cement_price_usd
    
    # Excavation volume (foundation + over-excavation)
    foundation_area = design.footing_length * design.footing_width
    over_excavation_factor = 1.2  # 20% over-excavation
    excavation_volume_per_footing = foundation_area * design.footing_depth * over_excavation_factor
    total_excavation_volume = 4.0 * excavation_volume_per_footing
    
    # Excavation cost (unchanged - uses fixed rate)
    excavation_cost = total_excavation_volume * EXCAVATION_RATE_PER_M3
    
    # Soil adjustment factor
    soil_factor = SOIL_FACTORS.get(inputs.soil_category, SOIL_FACTORS[SoilCategory.MEDIUM])
    
    # Total foundation cost
    base_foundation_cost = concrete_cost + excavation_cost
    foundation_cost = base_foundation_cost * soil_factor
    
    return foundation_cost


def _calculate_erection_cost(
    steel_cost: float,
    inputs: OptimizationInputs
) -> float:
    """
    Calculate transport & erection cost.
    
    Transport & erection cost = 0.25 × steel_cost
    
    Adjusted by terrain difficulty.
    
    Args:
        steel_cost: Steel cost in USD
        inputs: OptimizationInputs
        
    Returns:
        Erection cost in USD
    """
    # Base erection cost (25% of steel cost)
    base_erection_cost = 0.25 * steel_cost
    
    # Terrain multiplier
    terrain_multiplier = TERRAIN_MULTIPLIERS.get(
        inputs.terrain_type,
        TERRAIN_MULTIPLIERS[TerrainType.FLAT]
    )
    
    # Total erection cost
    return base_erection_cost * terrain_multiplier


def _calculate_land_cost(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> float:
    """
    Calculate tower footprint land / right-of-way cost per tower.
    
    This is the SECONDARY ROW component (tower footprint only).
    Corridor ROW cost is calculated separately at line level.
    
    Land footprint is approximated as base_width².
    
    Args:
        design: TowerDesign to cost
        inputs: OptimizationInputs with project location
        
    Returns:
        Tower footprint land cost per tower in USD
    """
    # Approximate tower land footprint (square base)
    footprint_area = design.base_width ** 2  # m²
    
    # Regional land rate (still using old region mapping for land rates)
    # TODO: Could add land rates to market_rates.py in future
    region = _get_region_from_location(inputs.project_location)
    land_rate = REGIONAL_LAND_RATES.get(region, REGIONAL_LAND_RATES["default"])
    
    # Tower footprint land cost per tower
    land_cost = footprint_area * land_rate
    
    return land_cost


def calculate_row_corridor_cost_per_km(
    inputs: OptimizationInputs,
    row_mode: str = "urban_private"
) -> float:
    """
    Calculate ROW corridor cost per kilometer.
    
    This is the DOMINANT ROW component representing:
    - Compensation under conductors
    - Land devaluation
    - Easements
    - Agricultural loss
    
    Formula:
      ROW_corridor_cost_per_km = corridor_width × land_rate × multiplier × 1000
    
    Args:
        inputs: OptimizationInputs with project location
        row_mode: ROW mode ("government_corridor", "rural_private", "urban_private", "mixed")
        
    Returns:
        ROW corridor cost per kilometer in USD/km
    """
    region = _get_region_from_location(inputs.project_location)
    base_corridor_width = REGIONAL_CORRIDOR_WIDTHS.get(region, REGIONAL_CORRIDOR_WIDTHS["default"])
    land_rate = REGIONAL_LAND_RATES.get(region, REGIONAL_LAND_RATES["default"])
    
    # Apply row_mode configuration
    row_config = ROW_MODE_CONFIG.get(row_mode, ROW_MODE_CONFIG["urban_private"])
    corridor_width = row_config["width_m"]
    multiplier = row_config["multiplier"]
    
    # ROW corridor cost per kilometer
    row_corridor_cost_per_km = corridor_width * land_rate * multiplier * 1000.0
    
    return row_corridor_cost_per_km


def check_cost_sanity(
    total_cost: float,
    voltage_level: float,
    tower_type: str
) -> Tuple[bool, str]:
    """
    Check if cost is within expected range for 400 kV suspension towers.
    
    Args:
        total_cost: Total cost in USD
        voltage_level: Voltage level in kV
        tower_type: Tower type string
        
    Returns:
        Tuple of (is_reasonable, warning_message)
    """
    # Check for 400 kV suspension towers
    if abs(voltage_level - 400.0) < 1.0 and tower_type == "suspension":
        if total_cost > 2000000.0:
            warning = (
                f"WARNING: Cost (${total_cost:,.2f} USD) exceeds typical "
                f"per-tower range for 400 kV suspension towers "
                f"($300,000 - $1,200,000 USD). Check inputs or geometry."
            )
            return False, warning
    
    return True, ""
