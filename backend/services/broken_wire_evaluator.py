"""
Broken-Wire (Unbalanced Load) Evaluator Module.

Evaluates tower safety under broken-wire conditions where one conductor is lost.
"""

from typing import Tuple, Optional
from data_models import TowerDesign, OptimizationInputs, TowerType
from backend.services.codal_engine import CodalEngine


def evaluate_broken_wire_case(
    design: TowerDesign,
    inputs: OptimizationInputs,
    codal_engine: CodalEngine,
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Evaluate tower safety under broken-wire (unbalanced load) condition.
    
    Simulates loss of one conductor and evaluates:
    - Base bending moment
    - Foundation uplift
    - Structural stability
    
    Args:
        design: TowerDesign to evaluate
        inputs: OptimizationInputs with project context
        codal_engine: CodalEngine for safety validation
        
    Returns:
        Tuple of (is_safe, violation_message, correction_suggestions)
        correction_suggestions dict contains: base_width_increase, foundation_increase, upgrade_type
    """
    if not inputs.include_broken_wire:
        return True, None, None  # Not evaluated
    
    # Simulate loss of one conductor
    # Typical 3-phase system: loss of one phase creates unbalanced transverse load
    
    # Calculate unbalanced transverse load
    # Simplified: assume conductor tension T, loss of one conductor creates
    # unbalanced force = T * sin(60°) for 3-phase system
    # For conservative estimate, use full conductor tension
    conductor_tension_kn = _estimate_conductor_tension(inputs.voltage_level, design.span_length)
    unbalanced_force_kn = conductor_tension_kn * 0.866  # sin(60°) for 3-phase
    
    # Calculate base bending moment from unbalanced load
    # Moment = Force × Height (simplified)
    base_bending_moment_knm = unbalanced_force_kn * design.tower_height
    
    # Calculate foundation uplift force
    # Uplift = Unbalanced force × lever arm / base_width
    # Simplified: uplift is proportional to bending moment and inversely proportional to base width
    uplift_force_kn = base_bending_moment_knm / max(design.base_width / 2.0, 1.0)  # Avoid division by zero
    
    # Evaluate against allowable limits
    # Conservative limits based on tower type
    allowable_bending_moment_knm = _get_allowable_bending_moment(design, inputs)
    allowable_uplift_kn = _get_allowable_uplift(design, inputs)
    
    violations = []
    correction_suggestions = {}
    
    # Check base bending moment
    if base_bending_moment_knm > allowable_bending_moment_knm:
        violations.append(f"Base bending moment {base_bending_moment_knm:.1f} kNm exceeds allowable {allowable_bending_moment_knm:.1f} kNm")
        # Suggest increasing base width
        required_base_width = design.base_width * (base_bending_moment_knm / allowable_bending_moment_knm) ** 0.5
        correction_suggestions['base_width_increase'] = max(0.0, required_base_width - design.base_width)
    
    # Check foundation uplift
    if uplift_force_kn > allowable_uplift_kn:
        violations.append(f"Foundation uplift {uplift_force_kn:.1f} kN exceeds allowable {allowable_uplift_kn:.1f} kN")
        # Suggest increasing foundation size or depth
        required_foundation_area = (design.footing_length * design.footing_width) * (uplift_force_kn / allowable_uplift_kn)
        correction_suggestions['foundation_increase'] = required_foundation_area - (design.footing_length * design.footing_width)
        correction_suggestions['foundation_depth_increase'] = 0.5  # Suggest 0.5m depth increase
        correction_suggestions['foundation_uplift_kn'] = uplift_force_kn  # Store for foundation evaluator
    
    # Check if tower type upgrade is needed
    if design.tower_type == TowerType.SUSPENSION and len(violations) > 0:
        correction_suggestions['upgrade_type'] = TowerType.TENSION
    
    is_safe = len(violations) == 0
    violation_message = "; ".join(violations) if violations else None
    
    return is_safe, violation_message, correction_suggestions if correction_suggestions else None


def apply_broken_wire_corrections(
    design: TowerDesign,
    correction_suggestions: dict,
) -> TowerDesign:
    """
    Apply auto-corrections for broken-wire violations.
    
    Args:
        design: Original TowerDesign
        correction_suggestions: Dict with correction suggestions from evaluate_broken_wire_case
        
    Returns:
        Corrected TowerDesign
    """
    from data_models import TowerDesign, FoundationType
    
    new_base_width = design.base_width
    new_footing_length = design.footing_length
    new_footing_width = design.footing_width
    new_footing_depth = design.footing_depth
    new_tower_type = design.tower_type
    
    # Apply base width increase
    if 'base_width_increase' in correction_suggestions:
        new_base_width = design.base_width + correction_suggestions['base_width_increase']
        # Clamp to reasonable maximum (40% of height)
        new_base_width = min(new_base_width, design.tower_height * 0.40)
    
    # Apply foundation size increase
    if 'foundation_increase' in correction_suggestions:
        # Increase foundation area proportionally
        current_area = design.footing_length * design.footing_width
        new_area = current_area + correction_suggestions['foundation_increase']
        # Maintain aspect ratio
        aspect_ratio = design.footing_length / design.footing_width
        new_footing_length = (new_area * aspect_ratio) ** 0.5
        new_footing_width = new_area / new_footing_length
        # Clamp to reasonable bounds
        new_footing_length = min(max(new_footing_length, 3.0), 8.0)
        new_footing_width = min(max(new_footing_width, 3.0), 8.0)
    
    # Apply foundation depth increase
    if 'foundation_depth_increase' in correction_suggestions:
        new_footing_depth = design.footing_depth + correction_suggestions['foundation_depth_increase']
        # Clamp to reasonable maximum
        new_footing_depth = min(new_footing_depth, 6.0)
    
    # Apply tower type upgrade
    if 'upgrade_type' in correction_suggestions:
        new_tower_type = correction_suggestions['upgrade_type']
    
    return TowerDesign(
        tower_type=new_tower_type,
        tower_height=design.tower_height,
        base_width=new_base_width,
        span_length=design.span_length,
        foundation_type=design.foundation_type,
        footing_length=new_footing_length,
        footing_width=new_footing_width,
        footing_depth=new_footing_depth,
    )


def _estimate_conductor_tension(voltage_kv: float, span_length_m: float) -> float:
    """Estimate conductor tension in kN based on voltage and span."""
    # Simplified estimation: tension increases with voltage and span
    # Typical values: 400kV ~50-80 kN, 765kV ~80-120 kN per conductor
    base_tension = 30.0  # kN base tension
    voltage_factor = voltage_kv / 400.0  # Normalize to 400kV
    span_factor = span_length_m / 300.0  # Normalize to 300m span
    
    tension_kn = base_tension * voltage_factor * span_factor
    return min(tension_kn, 150.0)  # Cap at 150 kN


def _get_allowable_bending_moment(design: TowerDesign, inputs: OptimizationInputs) -> float:
    """Get allowable base bending moment in kNm."""
    # Base capacity increases with base width and height
    base_capacity = 500.0  # kNm base capacity
    
    # Tower type multiplier
    type_multiplier = {
        TowerType.SUSPENSION: 1.0,
        TowerType.ANGLE: 1.2,
        TowerType.TENSION: 1.5,
        TowerType.DEAD_END: 2.0,
    }
    multiplier = type_multiplier.get(design.tower_type, 1.0)
    
    # Scale with base width
    width_factor = design.base_width / 10.0  # Normalize to 10m base
    
    return base_capacity * multiplier * width_factor


def _get_allowable_uplift(design: TowerDesign, inputs: OptimizationInputs) -> float:
    """Get allowable foundation uplift in kN."""
    # Foundation area and depth determine uplift capacity
    foundation_area = design.footing_length * design.footing_width  # m²
    
    # Soil bearing capacity (simplified)
    soil_capacity_kpa = {
        "soft": 50.0,
        "medium": 100.0,
        "hard": 200.0,
        "rock": 500.0,
    }
    bearing_capacity = soil_capacity_kpa.get(inputs.soil_category.value, 100.0)
    
    # Uplift capacity = bearing capacity × area × depth factor
    depth_factor = 1.0 + (design.footing_depth - 2.0) * 0.2  # Increase with depth
    uplift_capacity_kn = bearing_capacity * foundation_area * depth_factor / 10.0  # Convert to kN
    
    return uplift_capacity_kn

