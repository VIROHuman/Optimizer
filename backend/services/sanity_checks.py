"""
Real Project Sanity Checks.

Compares outputs against Tata / PowerGrid norms.
"""

from typing import Dict, List, Tuple, Any
from backend.models.canonical import CanonicalOptimizationResult


# Industry norms (Tata / PowerGrid benchmarks)
INDUSTRY_NORMS = {
    "tower_density_per_km": {
        "132kV": (2.0, 3.5),  # (min, max) towers/km
        "220kV": (2.2, 3.8),
        "400kV": (2.5, 4.0),
        "765kV": (2.8, 4.5),
    },
    "cost_per_km_usd": {
        "132kV": (50000, 150000),
        "220kV": (80000, 250000),
        "400kV": (150000, 400000),
        "765kV": (300000, 600000),
    },
    "avg_span_m": {
        "132kV": (300, 400),
        "220kV": (320, 420),
        "400kV": (350, 450),
        "765kV": (380, 450),
    },
}


def check_against_industry_norms(
    result: CanonicalOptimizationResult,
    voltage_kv: float,
) -> List[Dict[str, Any]]:
    """
    Compare results against industry norms.
    
    Args:
        result: CanonicalOptimizationResult
        voltage_kv: Voltage level in kV
        
    Returns:
        List of deviation warnings
    """
    warnings = []
    
    # Determine voltage category
    if voltage_kv <= 132:
        voltage_cat = "132kV"
    elif voltage_kv <= 220:
        voltage_cat = "220kV"
    elif voltage_kv <= 400:
        voltage_cat = "400kV"
    else:
        voltage_cat = "765kV"
    
    # Check tower density
    tower_density = result.line_summary.tower_density_per_km
    norm_range = INDUSTRY_NORMS["tower_density_per_km"][voltage_cat]
    if not (norm_range[0] <= tower_density <= norm_range[1]):
        warnings.append({
            "metric": "Tower Density",
            "value": f"{tower_density:.2f} towers/km",
            "norm_range": f"{norm_range[0]}-{norm_range[1]} towers/km",
            "deviation": "High" if tower_density > norm_range[1] else "Low",
        })
    
    # Check cost per km
    cost_per_km = result.line_summary.cost_per_km
    norm_range = INDUSTRY_NORMS["cost_per_km_usd"][voltage_cat]
    # Convert to USD if needed
    if result.cost_breakdown.currency == "INR":
        # Approximate conversion (should use actual rate)
        cost_per_km_usd = cost_per_km / 83.0
    else:
        cost_per_km_usd = cost_per_km
    
    if not (norm_range[0] <= cost_per_km_usd <= norm_range[1]):
        warnings.append({
            "metric": "Cost per km",
            "value": f"${cost_per_km_usd:.0f}/km",
            "norm_range": f"${norm_range[0]:.0f}-${norm_range[1]:.0f}/km",
            "deviation": "High" if cost_per_km_usd > norm_range[1] else "Low",
        })
    
    # Check average span
    avg_span = result.line_summary.avg_span_m
    norm_range = INDUSTRY_NORMS["avg_span_m"][voltage_cat]
    if not (norm_range[0] <= avg_span <= norm_range[1]):
        warnings.append({
            "metric": "Average Span",
            "value": f"{avg_span:.0f} m",
            "norm_range": f"{norm_range[0]}-{norm_range[1]} m",
            "deviation": "High" if avg_span > norm_range[1] else "Low",
        })
    
    return warnings

