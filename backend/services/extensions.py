"""
Tower Extensions Module.

Handles body extensions (height) and leg extensions (slope).
"""

from typing import Dict, Optional, Tuple
from data_models import TowerDesign, OptimizationInputs, TowerType, FoundationType
from cost_engine import calculate_cost_with_breakdown


def calculate_body_extension(
    base_design: TowerDesign,
    required_clearance: float,
    terrain_elevation: float,
    tower_elevation: float,
    inputs: OptimizationInputs,
) -> Tuple[float, float, str]:
    """
    Calculate body extension needed for terrain clearance.
    
    Args:
        base_design: Base tower design
        required_clearance: Required clearance above terrain
        terrain_elevation: Terrain elevation at clearance point
        tower_elevation: Tower base elevation
        inputs: OptimizationInputs
        
    Returns:
        Tuple of (extension_meters, cost_delta, governing_reason)
    """
    # Calculate required total height
    height_diff = terrain_elevation - tower_elevation
    required_total_height = base_design.tower_height + required_clearance + height_diff
    
    # Extension needed
    extension = max(0.0, required_total_height - base_design.tower_height)
    
    # Cost delta (approximate: extension steel cost)
    # Extension typically costs 15-20% of base tower cost per meter
    if extension > 0:
        _, base_cost_breakdown = calculate_cost_with_breakdown(base_design, inputs)
        extension_cost_per_m = base_cost_breakdown['steel_cost'] * 0.18 / base_design.tower_height
        cost_delta = extension * extension_cost_per_m
        governing_reason = f"Terrain clearance requires {extension:.1f}m extension"
    else:
        cost_delta = 0.0
        governing_reason = "No extension needed"
    
    return extension, cost_delta, governing_reason


def calculate_leg_extensions(
    tower_location: Dict[str, float],
    terrain_slope: float,
    foundation_size: Dict[str, float],
) -> Optional[Dict[str, float]]:
    """
    Calculate leg extensions for slope compensation.
    
    Args:
        tower_location: Tower location with elevation
        terrain_slope: Terrain slope in degrees
        foundation_size: Foundation dimensions
        
    Returns:
        Dict with leg extensions {leg_1: m, leg_2: m, leg_3: m, leg_4: m}
        or None if no extension needed
    """
    if abs(terrain_slope) < 2.0:  # Less than 2 degrees, no extension needed
        return None
    
    # Calculate extension based on slope
    # Extension = foundation_size * tan(slope)
    import math
    slope_rad = math.radians(terrain_slope)
    
    # For 4-legged tower, calculate per-leg extension
    # Simplified: assume slope affects two legs
    extension = foundation_size['width'] * math.tan(slope_rad) / 2.0
    
    if extension < 0.1:  # Less than 10cm, ignore
        return None
    
    return {
        "leg_1": extension,
        "leg_2": extension,
        "leg_3": 0.0,
        "leg_4": 0.0,
    }


def should_use_extension_vs_new_tower(
    extension_cost: float,
    new_tower_cost: float,
    extension_meters: float,
) -> Tuple[bool, str]:
    """
    Decide: extension vs new tower.
    
    Args:
        extension_cost: Cost of extension
        new_tower_cost: Cost of new tower
        extension_meters: Extension length needed
        
    Returns:
        Tuple of (use_extension: bool, reason: str)
    """
    if extension_meters > 15.0:  # More than 15m extension, prefer new tower
        return False, "Extension exceeds 15m limit - new tower preferred"
    
    if extension_cost < new_tower_cost * 0.7:  # Extension < 70% of new tower cost
        return True, f"Extension cheaper: {extension_cost:.0f} vs {new_tower_cost:.0f}"
    
    return False, f"New tower cheaper: {new_tower_cost:.0f} vs {extension_cost:.0f}"
