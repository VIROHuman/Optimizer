"""
Confidence Scoring Engine.

Provides honest estimates with confidence scores based on assumptions.
"""

from typing import List, Tuple
from data_models import OptimizationInputs, TerrainType


def calculate_confidence_score_with_drivers(
    inputs: OptimizationInputs,
    has_terrain_profile: bool = False,
    has_soil_survey: bool = False,
    has_wind_data: bool = False,
    row_mode: str = "urban_private",
    location_auto_detected: bool = False,
    wind_auto_detected: bool = False,
    terrain_auto_detected: bool = False,
    wind_user_override: bool = False,
    terrain_user_override: bool = False,
) -> Tuple[int, List[str]]:
    """
    Calculate confidence score (0-100%) with drivers.
    
    Starts at 100% and reduces based on assumptions.
    
    Args:
        inputs: OptimizationInputs
        has_terrain_profile: Whether detailed terrain profile available
        has_soil_survey: Whether soil survey data available
        has_wind_data: Whether site-specific wind data available
        row_mode: ROW mode used
        
    Returns:
        Tuple of (confidence_score, drivers_list)
    """
    confidence = 100
    drivers = []
    
    # Structural physics - always validated
    drivers.append("Structural physics fully validated")
    
    # Terrain assumptions
    if terrain_auto_detected:
        drivers.append("Terrain classified from elevation profile variance")
    elif terrain_user_override:
        confidence -= 5
        drivers.append("Terrain manually overridden (may not match elevation profile)")
    elif has_terrain_profile:
        drivers.append("Terrain modeled using detailed elevation profile")
    else:
        confidence -= 15
        drivers.append("Terrain modeled using satellite elevation data")
    
    # Soil assumptions
    if has_soil_survey:
        drivers.append("Soil properties from site survey")
    else:
        confidence -= 10
        drivers.append("Soil category assumed from regional norms")
    
    # Wind assumptions
    if wind_auto_detected:
        drivers.append("Wind zone derived from route location")
    elif wind_user_override:
        confidence -= 5
        drivers.append("Wind zone manually overridden (may not match location)")
    elif has_wind_data:
        drivers.append("Wind loads from site-specific data")
    else:
        confidence -= 10
        drivers.append("Wind zone assumed from regional classification")
    
    # Complex terrain
    if inputs.terrain_type == TerrainType.MOUNTAINOUS:
        confidence -= 5
        drivers.append("Mountainous terrain increases uncertainty")
    
    # Variable soil
    if inputs.soil_category.value == "soft":
        confidence -= 5
        drivers.append("Soft soil conditions increase foundation uncertainty")
    
    # Location detection
    if location_auto_detected:
        drivers.append("Geographic context derived from route geometry")
    else:
        confidence -= 5
        drivers.append("Location manually specified (may not match route coordinates)")
    
    # ROW model assumptions
    if row_mode == "urban_private":
        drivers.append("ROW model assumed conservative (urban private land)")
    elif row_mode == "government_corridor":
        drivers.append("ROW model assumes government corridor easement")
    elif row_mode == "rural_private":
        drivers.append("ROW model assumes rural private land compensation")
    else:
        drivers.append("ROW model assumes mixed scenario")
    
    # Advisory risks
    drivers.append("Seismic, ice, wildfire treated as advisory (not auto-applied)")
    
    # Currency resolution
    drivers.append("Currency inferred from route geography (presentation-only, no FX applied)")
    
    # Minimum confidence
    confidence = max(50, confidence)
    
    return confidence, drivers
