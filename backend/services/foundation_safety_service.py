"""
Foundation Safety Validation Service.

Post-optimization safety audit that checks:
1. Uplift stability (using existing foundation_uplift_evaluator)
2. Sliding stability (Rankine passive earth pressure)
3. Overturning stability (resisting moment vs overturning moment)

Auto-corrects unsafe foundations by increasing dimensions and calculates cost delta.
"""

import math
from typing import Dict, List, Any, Tuple, Optional
from data_models import (
    TowerDesign, OptimizationInputs, TowerType, FoundationType,
    TerrainType, WindZone, SoilCategory
)
from backend.services.foundation_uplift_evaluator import evaluate_foundation_uplift
from backend.data.market_rates import get_rates_for_country
from cost_engine import SOIL_FACTORS, EXCAVATION_RATE_PER_M3


# ============================================================================
# SOIL PROPERTIES (Standard geotechnical constants)
# ============================================================================

SOIL_PROPERTIES = {
    "soft": {
        "unit_weight_kn_m3": 16.0,  # kN/m3
        "angle_of_repose_deg": 25.0,  # degrees (updated from 20deg)
        "cohesion_kpa": 10.0,  # kPa
        "bearing_capacity_kpa": 150.0,  # kN/m2 (updated from 50.0)
    },
    "medium": {
        "unit_weight_kn_m3": 18.0,  # kN/m3
        "angle_of_repose_deg": 30.0,  # degrees
        "cohesion_kpa": 20.0,  # kPa
        "bearing_capacity_kpa": 250.0,  # kN/m2 (updated from 100.0)
    },
    "hard": {
        "unit_weight_kn_m3": 20.0,  # kN/m3
        "angle_of_repose_deg": 35.0,  # degrees
        "cohesion_kpa": 40.0,  # kPa
        "bearing_capacity_kpa": 450.0,  # kN/m2 (updated from 200.0)
    },
    "rock": {
        "unit_weight_kn_m3": 24.0,  # kN/m3
        "angle_of_repose_deg": 40.0,  # degrees
        "cohesion_kpa": 100.0,  # kPa
        "bearing_capacity_kpa": 500.0,  # kN/m2 (unchanged)
    },
}

# Minimum Factor of Safety required (updated to 1.5 for structural safety)
MIN_FOS = 1.5

# Fixed cost penalty for piling (when foundation exceeds 5.5m and still unsafe)
PILING_COST_PENALTY_USD = 50000.0  # $50,000 per tower requiring piling


def _get_country_code_from_location_helper(project_location: str) -> str:
    """Helper to get country code from location (duplicated from cost_engine)."""
    location_lower = project_location.lower().strip()
    
    country_mappings = {
        "india": "IN", "indian": "IN",
        "usa": "US", "united states": "US", "united states of america": "US", "america": "US",
        "canada": "CA", "mexico": "MX",
        "uk": "GB", "united kingdom": "GB", "britain": "GB", "england": "GB",
        "germany": "DE", "france": "FR", "italy": "IT", "spain": "ES",
        "netherlands": "NL", "belgium": "BE", "poland": "PL",
        "uae": "AE", "united arab emirates": "AE", "dubai": "AE",
        "saudi arabia": "SA", "qatar": "QA", "kuwait": "KW",
        "china": "CN", "japan": "JP", "south korea": "KR",
        "australia": "AU", "new zealand": "NZ",
        "south africa": "ZA", "egypt": "EG", "nigeria": "NG", "kenya": "KE",
    }
    
    if location_lower in country_mappings:
        return country_mappings[location_lower]
    
    for keyword, code in country_mappings.items():
        if keyword in location_lower:
            return code
    
    return "IN"  # Default


def _calculate_foundation_cost_helper(
    design: TowerDesign,
    inputs: OptimizationInputs,
    cement_price_usd: float
) -> float:
    """Helper to calculate foundation cost (duplicated from cost_engine)."""
    # Single footing volume
    single_footing_volume = (
        design.footing_length *
        design.footing_width *
        design.footing_depth
    )
    
    # Total concrete volume (4 footings)
    total_concrete_volume = 4.0 * single_footing_volume
    
    # Concrete cost
    base_concrete_rate = 160.0
    adjusted_concrete_rate = base_concrete_rate * (cement_price_usd / 150.0)
    concrete_cost = total_concrete_volume * adjusted_concrete_rate
    
    # Excavation volume
    foundation_area = design.footing_length * design.footing_width
    over_excavation_factor = 1.2
    excavation_volume_per_footing = foundation_area * design.footing_depth * over_excavation_factor
    total_excavation_volume = 4.0 * excavation_volume_per_footing
    
    # Excavation cost
    excavation_cost = total_excavation_volume * EXCAVATION_RATE_PER_M3
    
    # Soil adjustment factor
    soil_factor = SOIL_FACTORS.get(inputs.soil_category, SOIL_FACTORS[SoilCategory.MEDIUM])
    
    # Total foundation cost
    base_foundation_cost = concrete_cost + excavation_cost
    foundation_cost = base_foundation_cost * soil_factor
    
    return foundation_cost


def validate_tower_foundation(
    tower_data: Dict[str, Any],
    inputs: OptimizationInputs,
    project_location: str,
    auto_correct: bool = True,
) -> Dict[str, Any]:
    """
    Validate foundation safety for a single tower.
    
    Performs:
    1. Uplift check
    2. Sliding check
    3. Overturning check
    
    If auto_correct=True and FOS < MIN_FOS, automatically increases dimensions
    until safe, then calculates cost delta.
    
    Args:
        tower_data: TowerResponse dict with foundation_dimensions, total_height_m, etc.
        inputs: OptimizationInputs with soil, wind, terrain context
        project_location: Project location string for market rates
        auto_correct: If True, auto-correct unsafe foundations
        
    Returns:
        Dict with:
        - tower_id: int
        - status: "PASS" | "FAIL" | "ADJUSTED"
        - uplift_check: {is_safe, fos, total_uplift_kn, resistance_kn, governing_case}
        - sliding_check: {is_safe, fos, lateral_force_kn, resistance_kn}
        - overturning_check: {is_safe, fos, overturning_moment_knm, resisting_moment_knm}
        - original_cost: float
        - safety_cost_increase: float (if adjusted)
        - adjusted_dimensions: Dict (if adjusted)
        - reason: str
    """
    # Extract foundation dimensions
    foundation_dims = tower_data.get("foundation_dimensions", {})
    footing_length = foundation_dims.get("length", 4.0)
    footing_width = foundation_dims.get("width", 4.0)
    footing_depth = foundation_dims.get("depth", 3.0)
    tower_height = tower_data.get("total_height_m", 40.0)
    tower_base_width = tower_data.get("base_width_m", 8.0)
    
    # Convert to TowerDesign for existing evaluators
    tower_type_str = tower_data.get("tower_type", "suspension")
    tower_type = TowerType[tower_type_str.upper()] if hasattr(TowerType, tower_type_str.upper()) else TowerType.SUSPENSION
    
    foundation_type_str = tower_data.get("foundation_type", "pad_footing")
    foundation_type = FoundationType.PAD_FOOTING
    if foundation_type_str == "chimney_footing":
        foundation_type = FoundationType.CHIMNEY_FOOTING
    
    # Create TowerDesign
    design = TowerDesign(
        tower_type=tower_type,
        tower_height=tower_height,
        base_width=tower_base_width,
        span_length=350.0,  # Default span (not critical for foundation checks)
        foundation_type=foundation_type,
        footing_length=footing_length,
        footing_width=footing_width,
        footing_depth=footing_depth,
    )
    
    # Store original dimensions
    original_length = footing_length
    original_width = footing_width
    original_depth = footing_depth
    
    # Get original cost
    country_code = _get_country_code_from_location_helper(project_location)
    rates = get_rates_for_country(country_code)
    original_cost = _calculate_foundation_cost_helper(design, inputs, rates['cement_price_usd'])
    
    # Perform checks
    max_iterations = 20
    iteration = 0
    adjusted = False
    
    while iteration < max_iterations:
        # Update design with current dimensions
        design = TowerDesign(
            tower_type=tower_type,
            tower_height=tower_height,
            base_width=tower_base_width,
            span_length=350.0,
            foundation_type=foundation_type,
            footing_length=footing_length,
            footing_width=footing_width,
            footing_depth=footing_depth,
        )
        
        # Check 1: Uplift (get direct wind uplift for reference)
        uplift_safe, uplift_kn, uplift_case, required_depth = evaluate_foundation_uplift(
            design, inputs, broken_wire_uplift_kn=None
        )
        uplift_resistance = _compute_foundation_resistance_for_uplift(design, inputs)
        
        # Check 2: Sliding
        sliding_safe, sliding_fos, lateral_force, sliding_resistance = _check_sliding(
            design, inputs
        )
        
        # Get span_length from tower_data if available (for conductor wind load)
        span_length = tower_data.get("span_length_m", None)
        if span_length is None:
            # Try to get from design
            span_length = design.span_length if hasattr(design, 'span_length') and design.span_length > 0 else None
        
        # Check 3: Overturning (now includes conductor wind load)
        overturning_safe, overturning_fos, overturning_moment, resisting_moment = _check_overturning(
            design, inputs, tower_height, span_length=span_length
        )
        
        # ========================================================================
        # CALCULATE ACTUAL UPLIFT FORCE FROM OVERTURNING MOMENT
        # ========================================================================
        # The "Uplift Force" displayed should be the reaction uplift from the
        # overturning moment, not the direct vertical wind load.
        # Formula: uplift_force = total_overturning_moment / base_width
        actual_uplift_force_kn = overturning_moment / tower_base_width if tower_base_width > 0 else 0.0
        
        # Use the actual uplift force for FOS calculation (moment-derived is the correct value)
        # This is the actual reaction force that the foundation must resist
        uplift_kn_for_display = actual_uplift_force_kn
        
        # Calculate FOS using actual uplift force from moment (not direct wind uplift)
        # This gives the correct FOS: resistance / actual_force
        uplift_fos = uplift_resistance / actual_uplift_force_kn if actual_uplift_force_kn > 0 else float('inf')
        
        # All checks pass?
        all_safe = (
            uplift_fos >= MIN_FOS and
            sliding_fos >= MIN_FOS and
            overturning_fos >= MIN_FOS
        )
        
        if all_safe:
            break
        
        # Auto-correct if enabled
        if auto_correct and not all_safe:
            adjusted = True
            # Increase dimensions by 0.25m steps (as per requirements)
            if uplift_fos < MIN_FOS:
                # Increase depth for uplift
                footing_depth = min(footing_depth + 0.25, 6.0)  # Max 6m for shallow
            if sliding_fos < MIN_FOS:
                # Increase width for sliding (more passive pressure area)
                footing_width = min(footing_width + 0.25, 5.5)  # Max 5.5m for pad foundation
                footing_length = min(footing_length + 0.25, 5.5)  # Keep square-ish, max 5.5m
            if overturning_fos < MIN_FOS:
                # Increase width/length for overturning (larger base = more resisting moment)
                footing_width = min(footing_width + 0.25, 5.5)  # Max 5.5m
                footing_length = min(footing_length + 0.25, 5.5)  # Max 5.5m
        else:
            # No auto-correction, just report failure
            break
        
        iteration += 1
    
    # Check if max dimension reached and still unsafe (requires piling)
    max_dimension_reached = (footing_width >= 5.5 or footing_length >= 5.5) and not all_safe
    
    # Calculate final cost if adjusted
    safety_cost_increase = 0.0
    adjusted_dimensions = None
    if max_dimension_reached:
        # Apply fixed high cost penalty for piling
        safety_cost_increase = PILING_COST_PENALTY_USD
        adjusted_dimensions = {
            "length": footing_length,
            "width": footing_width,
            "depth": footing_depth,
        }
    elif adjusted:
        final_cost = _calculate_foundation_cost_helper(design, inputs, rates['cement_price_usd'])
        safety_cost_increase = final_cost - original_cost
        adjusted_dimensions = {
            "length": footing_length,
            "width": footing_width,
            "depth": footing_depth,
        }
    
    # Determine status
    if max_dimension_reached:
        status = "REQUIRES_PILING"
        reason = "Foundation dimensions reached maximum (5.5m) but still unsafe. Piling required."
    elif all_safe and not adjusted:
        status = "PASS"
        reason = "All safety checks passed"
    elif all_safe and adjusted:
        status = "ADJUSTED"
        reasons = []
        if uplift_fos < MIN_FOS:
            reasons.append(f"Increased depth by {footing_depth - original_depth:.2f}m for uplift")
        if sliding_fos < MIN_FOS:
            reasons.append(f"Increased width by {footing_width - original_width:.2f}m for sliding")
        if overturning_fos < MIN_FOS:
            reasons.append(f"Increased dimensions for overturning")
        reason = "; ".join(reasons) if reasons else "Dimensions adjusted for safety"
    else:
        status = "FAIL"
        reasons = []
        if uplift_fos < MIN_FOS:
            reasons.append(f"Uplift FOS {uplift_fos:.2f} < {MIN_FOS}")
        if sliding_fos < MIN_FOS:
            reasons.append(f"Sliding FOS {sliding_fos:.2f} < {MIN_FOS}")
        if overturning_fos < MIN_FOS:
            reasons.append(f"Overturning FOS {overturning_fos:.2f} < {MIN_FOS}")
        reason = "; ".join(reasons)
    
    return {
        "tower_id": tower_data.get("index", 0),
        "status": status,
        "uplift_check": {
            "is_safe": uplift_fos >= MIN_FOS,
            "fos": round(uplift_fos, 3),
            "total_uplift_kn": round(uplift_kn_for_display, 2),  # Use moment-derived uplift for display
            "resistance_kn": round(uplift_resistance, 2),
            "governing_case": uplift_case,
            "direct_wind_uplift_kn": round(uplift_kn, 2),  # Keep original for reference
            "reaction_uplift_from_moment_kn": round(actual_uplift_force_kn, 2),  # The actual uplift force
        },
        "sliding_check": {
            "is_safe": sliding_fos >= MIN_FOS,
            "fos": round(sliding_fos, 3),
            "lateral_force_kn": round(lateral_force, 2),
            "resistance_kn": round(sliding_resistance, 2),
        },
        "overturning_check": {
            "is_safe": overturning_fos >= MIN_FOS,
            "fos": round(overturning_fos, 3),
            "overturning_moment_knm": round(overturning_moment, 2),
            "resisting_moment_knm": round(resisting_moment, 2),
        },
        "original_cost": round(original_cost, 2),
        "safety_cost_increase": round(safety_cost_increase, 2),
        "adjusted_dimensions": adjusted_dimensions,
        "reason": reason,
    }


def _compute_foundation_resistance_for_uplift(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> float:
    """Compute foundation resistance to uplift (same as foundation_uplift_evaluator)."""
    foundation_area = design.footing_length * design.footing_width  # m2
    
    # Use soil properties from SOIL_PROPERTIES (updated values)
    soil_props = SOIL_PROPERTIES.get(inputs.soil_category.value, SOIL_PROPERTIES["medium"])
    bearing_capacity = soil_props["bearing_capacity_kpa"]
    
    # Depth factor
    depth_factor = 1.0 + (design.footing_depth - 2.0) * 0.3
    depth_factor = max(1.0, depth_factor)
    
    # Foundation weight
    foundation_volume_m3 = foundation_area * design.footing_depth
    foundation_weight_kn = foundation_volume_m3 * 24.0  # Concrete density ~24 kN/m3
    
    # Total resistance
    resistance_kn = (bearing_capacity * foundation_area * depth_factor / 10.0) + foundation_weight_kn
    
    return resistance_kn


def _check_sliding(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> Tuple[bool, float, float, float]:
    """
    Check sliding stability using Rankine passive earth pressure.
    
    FOS must be > 1.5 for structural safety.
    
    Returns:
        (is_safe, fos, lateral_force_kn, resistance_kn)
    """
    soil_props = SOIL_PROPERTIES.get(inputs.soil_category.value, SOIL_PROPERTIES["medium"])
    unit_weight = soil_props["unit_weight_kn_m3"]
    angle_repose = math.radians(soil_props["angle_of_repose_deg"])
    cohesion = soil_props["cohesion_kpa"]
    
    # Passive earth pressure coefficient (Rankine)
    Kp = (1 + math.sin(angle_repose)) / (1 - math.sin(angle_repose))
    
    # Foundation depth
    D = design.footing_depth
    
    # Calculate passive earth pressure at different depths (layered approach)
    # Divide depth into 5 layers (as per Excel reference)
    num_layers = 5
    layer_depth = D / num_layers
    total_passive_force_kn = 0.0
    
    # Foundation face area (perimeter x depth for each layer)
    # For square footing: perimeter = 4 x width
    foundation_perimeter = 4.0 * design.footing_width  # meters
    
    for i in range(num_layers):
        # Depth to center of layer
        depth_to_layer = (i + 0.5) * layer_depth
        
        # Passive pressure at this depth (Rankine)
        passive_pressure_kpa = (
            unit_weight * depth_to_layer * Kp +
            2 * cohesion * math.sqrt(Kp)
        )
        
        # Force from this layer = pressure x area
        layer_area_m2 = foundation_perimeter * layer_depth
        layer_force_kn = (passive_pressure_kpa * layer_area_m2) / 1000.0  # Convert to kN
        
        total_passive_force_kn += layer_force_kn
    
    # Additional resistance from foundation base friction
    # Friction coefficient for concrete-soil interface
    friction_coefficient = 0.6  # Typical for concrete on soil
    foundation_weight_kn = (
        design.footing_length * design.footing_width * design.footing_depth * 24.0
    )  # Concrete weight
    friction_resistance_kn = foundation_weight_kn * friction_coefficient
    
    # Total sliding resistance
    total_resistance_kn = total_passive_force_kn + friction_resistance_kn
    
    # Lateral force (wind + broken wire if applicable) - for sliding, use total force (tower + conductors)
    tower_body_force_kn, conductor_force_kn = _compute_lateral_force(design, inputs, span_length=None)
    lateral_force_kn = tower_body_force_kn + conductor_force_kn
    
    # Factor of Safety
    fos = total_resistance_kn / lateral_force_kn if lateral_force_kn > 0 else float('inf')
    is_safe = fos >= MIN_FOS
    
    return is_safe, fos, lateral_force_kn, total_resistance_kn


def _compute_lateral_force(
    design: TowerDesign,
    inputs: OptimizationInputs,
    span_length: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Compute lateral forces (tower body + conductors) in kN.
    
    Returns:
        Tuple of (tower_body_force_kn, conductor_force_kn)
    """
    # Wind pressure
    wind_pressure_kpa = {
        "zone_1": 0.5,
        "zone_2": 0.8,
        "zone_3": 1.2,
        "zone_4": 1.8,
    }
    pressure = wind_pressure_kpa.get(inputs.wind_zone.value, 0.8)
    
    if inputs.design_for_higher_wind:
        pressure *= 1.3
    
    # Convert to kN/m²
    wind_pressure_kn_m2 = pressure
    
    # ========================================================================
    # TOWER BODY WIND LOAD
    # ========================================================================
    # Tower area (simplified)
    tower_area_m2 = design.tower_height * design.base_width
    drag_coefficient = 1.2  # Typical for lattice towers
    
    # Lateral force from wind on tower body
    tower_body_force_kn = (wind_pressure_kn_m2 * tower_area_m2 * drag_coefficient) / 10.0  # Convert to kN
    
    # Add broken wire force if applicable (simplified)
    if inputs.include_broken_wire:
        # Broken wire creates significant lateral force
        # Simplified: ~30% of vertical load
        vertical_load_kn = design.tower_height * design.base_width * 0.5  # Approximate
        broken_wire_lateral_kn = vertical_load_kn * 0.3
        tower_body_force_kn += broken_wire_lateral_kn
    
    # ========================================================================
    # CONDUCTOR WIND LOAD (Wind Span)
    # ========================================================================
    # Constants
    CONDUCTOR_DIAMETER = 0.03  # 30mm for ACSR Zebra (typical for 220-400kV)
    NUM_PHASES = 3  # Standard single circuit (Double circuit = 6, but use 3 for safety)
    DRAG_COEFF_WIRE = 1.0
    
    # Use span_length from design or provided parameter, default to 350m
    safe_span = span_length if span_length is not None else (design.span_length if hasattr(design, 'span_length') and design.span_length > 0 else 350.0)
    
    # Wire projected area = span_length × diameter × number of phases
    wire_projected_area = safe_span * CONDUCTOR_DIAMETER * NUM_PHASES
    
    # Conductor wind force
    conductor_force_kn = wind_pressure_kn_m2 * wire_projected_area * DRAG_COEFF_WIRE
    
    return tower_body_force_kn, conductor_force_kn


def _check_overturning(
    design: TowerDesign,
    inputs: OptimizationInputs,
    tower_height: float,
    span_length: Optional[float] = None,
) -> Tuple[bool, float, float, float]:
    """
    Check overturning stability.
    
    Includes wind load on both tower body and conductors (wind span).
    FOS must be > 1.5 for structural safety.
    
    Args:
        design: TowerDesign with dimensions
        inputs: OptimizationInputs with wind zone, soil, etc.
        tower_height: Tower height in meters
        span_length: Optional span length in meters (defaults to design.span_length or 350m)
    
    Returns:
        (is_safe, fos, overturning_moment_knm, resisting_moment_knm)
    """
    # Get lateral forces (tower body + conductors)
    tower_body_force_kn, conductor_force_kn = _compute_lateral_force(design, inputs, span_length)
    
    # ========================================================================
    # TOWER BODY MOMENT
    # ========================================================================
    # Moment arm = tower height (center of wind pressure at ~0.6H for tower body)
    moment_arm_tower = tower_height * 0.6
    moment_tower = tower_body_force_kn * moment_arm_tower
    
    # ========================================================================
    # CONDUCTOR MOMENT
    # ========================================================================
    # Conductor force acts at tower top (height = tower_height)
    moment_wires = conductor_force_kn * tower_height
    
    # ========================================================================
    # TOTAL OVERTURNING MOMENT
    # ========================================================================
    total_overturning_moment_knm = moment_tower + moment_wires
    
    # Resisting moment = foundation weight x lever arm
    # Foundation weight
    foundation_volume_m3 = (
        design.footing_length * design.footing_width * design.footing_depth
    )
    foundation_weight_kn = foundation_volume_m3 * 24.0  # Concrete density
    
    # Lever arm = foundation width / 2 (moment about edge)
    lever_arm_m = design.footing_width / 2.0
    resisting_moment_knm = foundation_weight_kn * lever_arm_m
    
    # Additional resisting moment from soil weight above foundation
    # (Soil weight contributes to stability)
    soil_props = SOIL_PROPERTIES.get(inputs.soil_category.value, SOIL_PROPERTIES["medium"])
    unit_weight = soil_props["unit_weight_kn_m3"]
    soil_weight_kn = (
        design.footing_length * design.footing_width * design.footing_depth * unit_weight
    )
    soil_resisting_moment_knm = soil_weight_kn * lever_arm_m
    
    total_resisting_moment_knm = resisting_moment_knm + soil_resisting_moment_knm
    
    # Factor of Safety
    fos = total_resisting_moment_knm / total_overturning_moment_knm if total_overturning_moment_knm > 0 else float('inf')
    is_safe = fos >= MIN_FOS
    
    return is_safe, fos, total_overturning_moment_knm, total_resisting_moment_knm


def validate_all_towers(
    towers: List[Dict[str, Any]],
    inputs: OptimizationInputs,
    project_location: str,
    auto_correct: bool = True,
) -> Dict[str, Any]:
    """
    Validate foundation safety for all towers.
    
    Args:
        towers: List of TowerResponse dicts
        inputs: OptimizationInputs
        project_location: Project location string
        auto_correct: If True, auto-correct unsafe foundations
        
    Returns:
        Dict with:
        - summary: {uplift_passed, sliding_passed, overturning_passed, total_towers}
        - tower_results: List of individual tower validation results
        - critical_alerts: List of high-risk towers
        - total_safety_cost_increase: float
    """
    tower_results = []
    uplift_passed = 0
    sliding_passed = 0
    overturning_passed = 0
    critical_alerts = []
    total_safety_cost_increase = 0.0
    
    for tower in towers:
        result = validate_tower_foundation(tower, inputs, project_location, auto_correct)
        tower_results.append(result)
        
        # Count passes
        if result["uplift_check"]["is_safe"]:
            uplift_passed += 1
        if result["sliding_check"]["is_safe"]:
            sliding_passed += 1
        if result["overturning_check"]["is_safe"]:
            overturning_passed += 1
        
        # Identify critical alerts (FOS < 1.0 even after correction attempt)
        if result["status"] == "FAIL":
            critical_alerts.append({
                "tower_id": result["tower_id"],
                "risk": "HIGH",
                "issues": [
                    f"Uplift FOS: {result['uplift_check']['fos']:.2f}" if not result["uplift_check"]["is_safe"] else None,
                    f"Sliding FOS: {result['sliding_check']['fos']:.2f}" if not result["sliding_check"]["is_safe"] else None,
                    f"Overturning FOS: {result['overturning_check']['fos']:.2f}" if not result["overturning_check"]["is_safe"] else None,
                ],
            })
            # Remove None values
            critical_alerts[-1]["issues"] = [i for i in critical_alerts[-1]["issues"] if i is not None]
        
        # Sum cost increases
        total_safety_cost_increase += result.get("safety_cost_increase", 0.0)
    
    return {
        "summary": {
            "uplift_passed": uplift_passed,
            "sliding_passed": sliding_passed,
            "overturning_passed": overturning_passed,
            "total_towers": len(towers),
        },
        "tower_results": tower_results,
        "critical_alerts": critical_alerts,
        "total_safety_cost_increase": round(total_safety_cost_increase, 2),
    }

