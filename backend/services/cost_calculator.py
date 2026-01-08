"""
Cost Calculator Service.

Enhanced cost calculation with AI-powered market rates via MarketOracle.
This service provides real-time, location-based pricing for tower designs.
"""

import logging
from typing import Dict, Optional, Tuple
from data_models import TowerDesign, OptimizationInputs
from backend.services.market_oracle import get_rates
from cost_engine import (
    _calculate_steel_cost,
    _calculate_foundation_cost,
    _calculate_erection_cost,
    _calculate_land_cost,
)

logger = logging.getLogger(__name__)


def calculate_tower_cost(
    design: TowerDesign,
    inputs: OptimizationInputs,
    geo_context: Optional[Dict] = None
) -> Tuple[float, Dict]:
    """
    Calculate tower cost using AI-powered market rates.
    
    Args:
        design: TowerDesign to cost
        inputs: OptimizationInputs containing project context
        geo_context: Optional geographic context with country_name and state
        
    Returns:
        Tuple of (total_cost, metadata_dict)
        metadata_dict contains:
        - steel_cost
        - foundation_cost
        - erection_cost
        - land_cost
        - total_cost
        - currency_symbol
        - currency_code
        - market_note
        - market_source
    """
    # Extract country and region from geo_context or fallback to project_location
    country = None
    region = None
    
    if geo_context:
        country = geo_context.get("country_name")
        region = geo_context.get("state")
    
    # Fallback to project_location if geo_context not available
    if not country:
        country = inputs.project_location
    
    # Get real-time market rates from MarketOracle
    try:
        rates = get_rates(country, region)
        logger.info(f"CostCalculator: Using MarketOracle rates for {country} ({region or 'no region'})")
    except Exception as e:
        logger.error(f"CostCalculator: Failed to get MarketOracle rates: {e}. Using fallback.")
        # Import fallback from market_oracle
        from backend.services.market_oracle import FALLBACK_RATES
        rates = FALLBACK_RATES.copy()
    
    # Validate steel price (per tonne)
    steel_price_usd = rates['steel_price_usd']
    if steel_price_usd < 100.0 or steel_price_usd > 5000.0:
        logger.warning(
            f"Steel price {steel_price_usd} outside expected range (100-5000 USD/tonne). "
            f"Using value anyway."
        )
    
    # Component 1: Steel cost (using AI market rates)
    steel_cost = _calculate_steel_cost(design, inputs, steel_price_usd)
    
    # Component 2: Foundation materials cost (using AI market rates)
    # Note: MarketOracle returns 'concrete_price_usd', but cost_engine expects 'cement_price_usd'
    # They're equivalent for our purposes
    concrete_price_usd = rates.get('concrete_price_usd', rates.get('cement_price_usd', 120.0))
    foundation_cost = _calculate_foundation_cost(design, inputs, concrete_price_usd)
    
    # Component 3: Transport & Erection cost (using AI market rates)
    erection_cost_base = _calculate_erection_cost(steel_cost, inputs)
    # Apply labor and logistics factors from AI market rates
    labor_factor = rates.get('labor_factor', 2.0)
    logistics_factor = rates.get('logistics_factor', 1.3)
    erection_cost = erection_cost_base * labor_factor * logistics_factor
    
    # Component 4: Land / Right-of-Way cost
    land_cost = _calculate_land_cost(design, inputs)
    
    # Total per-tower cost
    total_cost = steel_cost + foundation_cost + erection_cost + land_cost
    
    # Prepare metadata for frontend display
    metadata = {
        "steel_cost": steel_cost,
        "foundation_cost": foundation_cost,
        "erection_cost": erection_cost,
        "land_cost": land_cost,
        "total_cost": total_cost,
        "currency_symbol": rates.get('currency_symbol', '$'),
        "currency_code": rates.get('currency_code', 'USD'),
        "market_note": rates.get('market_note', 'Real-time market rates'),
        "market_source": rates.get('source', 'unknown'),
        "steel_price_usd": steel_price_usd,
        "concrete_price_usd": concrete_price_usd,
        "labor_factor": labor_factor,
        "logistics_factor": logistics_factor,
        "country": country,
        "region": region,
    }
    
    # Store metadata in design object for frontend access (if design has a metadata attribute)
    # Note: TowerDesign may not have this, so we'll return it in the metadata dict instead
    
    logger.debug(
        f"CostCalculator: Calculated cost for {design.tower_type.value} tower: "
        f"${total_cost:.2f} ({metadata['currency_symbol']})"
    )
    
    return total_cost, metadata

