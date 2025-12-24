"""
Foundation Uplift and Depth-Based Stability Evaluator Module.

Evaluates foundation stability under uplift forces from wind, broken wire, and terrain slope.
"""

from typing import Tuple, Optional
from data_models import TowerDesign, OptimizationInputs


def evaluate_foundation_uplift(
    design: TowerDesign,
    inputs: OptimizationInputs,
    broken_wire_uplift_kn: Optional[float] = None,
) -> Tuple[bool, float, Optional[str], float]:
    """
    Evaluate foundation stability under uplift forces.
    
    Computes uplift from:
    - Wind loads
    - Broken wire (if enabled)
    - Terrain slope (leg differential)
    
    Args:
        design: TowerDesign to evaluate
        inputs: OptimizationInputs with project context
        broken_wire_uplift_kn: Uplift force from broken-wire case (if evaluated)
        
    Returns:
        Tuple of (is_safe, total_uplift_kn, governing_case, required_depth_m)
        If is_safe=False, required_depth_m is the depth needed for safety
    """
    # Compute uplift forces from various sources
    wind_uplift_kn = _compute_wind_uplift(design, inputs)
    terrain_uplift_kn = _compute_terrain_uplift(design, inputs)
    
    # Total uplift force
    total_uplift_kn = wind_uplift_kn + terrain_uplift_kn
    if broken_wire_uplift_kn is not None:
        total_uplift_kn += broken_wire_uplift_kn
    
    # Determine governing case
    governing_case = None
    if broken_wire_uplift_kn is not None and broken_wire_uplift_kn > wind_uplift_kn:
        governing_case = "Broken wire"
    elif terrain_uplift_kn > wind_uplift_kn:
        governing_case = "Terrain slope"
    else:
        governing_case = "Wind load"
    
    # Evaluate foundation resistance
    foundation_resistance_kn = _compute_foundation_resistance(design, inputs)
    
    # Check if uplift exceeds resistance
    is_safe = total_uplift_kn <= foundation_resistance_kn
    
    # If unsafe, calculate required depth iteratively
    required_depth_m = design.footing_depth
    if not is_safe:
        required_depth_m = _calculate_required_depth(
            design, inputs, total_uplift_kn, broken_wire_uplift_kn
        )
    
    return is_safe, total_uplift_kn, governing_case, required_depth_m


def _compute_wind_uplift(design: TowerDesign, inputs: OptimizationInputs) -> float:
    """Compute uplift force from wind loads in kN."""
    # Wind pressure increases with wind zone
    wind_pressure_kpa = {
        "zone_1": 0.5,
        "zone_2": 0.8,
        "zone_3": 1.2,
        "zone_4": 1.8,
    }
    pressure = wind_pressure_kpa.get(inputs.wind_zone.value, 0.8)
    
    # Higher wind if design_for_higher_wind is enabled
    if inputs.design_for_higher_wind:
        pressure *= 1.3
    
    # Wind uplift = pressure × tower area × uplift coefficient
    # Tower area approximated as height × base_width
    tower_area_m2 = design.tower_height * design.base_width
    uplift_coefficient = 0.3  # Typical for lattice towers
    
    uplift_kn = pressure * tower_area_m2 * uplift_coefficient / 10.0  # Convert to kN
    return uplift_kn


def _compute_terrain_uplift(design: TowerDesign, inputs: OptimizationInputs) -> float:
    """Compute uplift force from terrain slope (leg differential) in kN."""
    # Terrain slope creates differential loading on tower legs
    # More significant in mountainous terrain
    
    terrain_factor = {
        "flat": 0.0,
        "rolling": 0.1,
        "mountainous": 0.3,
        "desert": 0.05,
    }
    slope_factor = terrain_factor.get(inputs.terrain_type.value, 0.1)
    
    # Uplift from terrain = tower weight × slope factor
    # Simplified: assume tower weight proportional to height × base_width
    tower_weight_factor = design.tower_height * design.base_width / 100.0
    uplift_kn = tower_weight_factor * slope_factor
    
    return uplift_kn


def _compute_foundation_resistance(design: TowerDesign, inputs: OptimizationInputs) -> float:
    """Compute foundation resistance to uplift in kN."""
    foundation_area = design.footing_length * design.footing_width  # m²
    
    # Soil bearing capacity (kPa)
    soil_capacity_kpa = {
        "soft": 50.0,
        "medium": 100.0,
        "hard": 200.0,
        "rock": 500.0,
    }
    bearing_capacity = soil_capacity_kpa.get(inputs.soil_category.value, 100.0)
    
    # Uplift resistance = bearing capacity × area × depth factor
    # Depth factor increases resistance with depth
    depth_factor = 1.0 + (design.footing_depth - 2.0) * 0.3  # 30% increase per meter above 2m
    depth_factor = max(1.0, depth_factor)  # Minimum 1.0
    
    # Additional resistance from foundation weight
    # Concrete density ~24 kN/m³
    foundation_volume_m3 = foundation_area * design.footing_depth
    foundation_weight_kn = foundation_volume_m3 * 24.0
    
    # Total resistance = bearing + weight
    resistance_kn = (bearing_capacity * foundation_area * depth_factor / 10.0) + foundation_weight_kn
    
    return resistance_kn


def _calculate_required_depth(
    design: TowerDesign,
    inputs: OptimizationInputs,
    total_uplift_kn: float,
    broken_wire_uplift_kn: Optional[float],
) -> float:
    """
    Calculate required foundation depth iteratively to resist uplift.
    
    Args:
        design: TowerDesign
        inputs: OptimizationInputs
        total_uplift_kn: Total uplift force
        broken_wire_uplift_kn: Broken wire uplift (if applicable)
        
    Returns:
        Required foundation depth in meters
    """
    # Start with current depth
    current_depth = design.footing_depth
    max_iterations = 20
    depth_increment = 0.1  # 10cm increments
    
    for _ in range(max_iterations):
        # Create test design with current depth
        test_design = TowerDesign(
            tower_type=design.tower_type,
            tower_height=design.tower_height,
            base_width=design.base_width,
            span_length=design.span_length,
            foundation_type=design.foundation_type,
            footing_length=design.footing_length,
            footing_width=design.footing_width,
            footing_depth=current_depth,
        )
        
        # Check resistance
        resistance_kn = _compute_foundation_resistance(test_design, inputs)
        
        if resistance_kn >= total_uplift_kn:
            return current_depth
        
        # Increase depth
        current_depth += depth_increment
        
        # Safety limit: don't exceed 6m for shallow foundations
        if current_depth > 6.0:
            return 6.0
    
    # If iteration limit reached, return maximum
    return min(current_depth, 6.0)


