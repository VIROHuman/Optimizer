"""
Cost Sensitivity Bands.

Computes ± variance for DPR realism.
"""

from typing import Dict, Tuple
from data_models import OptimizationInputs
from regional_risk_registry import get_regional_risks


def calculate_cost_sensitivity_bands(
    base_cost: float,
    inputs: OptimizationInputs,
) -> Dict[str, float]:
    """
    Calculate cost sensitivity bands (± variance).
    
    Args:
        base_cost: Base cost estimate
        inputs: OptimizationInputs
        
    Returns:
        Dict with {lower_bound, upper_bound, variance_percent}
    """
    # Base variance factors
    variance_percent = 15.0  # Default ±15%
    
    # Increase variance for complex terrain
    if inputs.terrain_type.value == "mountainous":
        variance_percent += 10.0
    
    # Increase variance for soft soil
    if inputs.soil_category.value == "soft":
        variance_percent += 5.0
    
    # Increase variance for high wind
    if inputs.wind_zone.value in ["zone_3", "zone_4"]:
        variance_percent += 5.0
    
    # Increase variance for high voltage
    if inputs.voltage_level >= 400:
        variance_percent += 5.0
    
    # Get regional risks
    regional_risks = get_regional_risks(inputs.project_location) or []
    if len(regional_risks) > 3:
        variance_percent += 5.0  # More risks = more uncertainty
    
    # Calculate bounds
    variance_factor = variance_percent / 100.0
    lower_bound = base_cost * (1.0 - variance_factor)
    upper_bound = base_cost * (1.0 + variance_factor)
    
    return {
        "lower_bound": round(lower_bound, 2),
        "upper_bound": round(upper_bound, 2),
        "variance_percent": round(variance_percent, 1),
        "expected_range": f"{lower_bound:.0f} - {upper_bound:.0f}",
    }


