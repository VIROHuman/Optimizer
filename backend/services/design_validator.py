"""
Design validation utilities.

This module provides validation functions that return violation lists
instead of raising exceptions. This ensures the API always returns
structured responses, never crashes.
"""

from typing import List, Tuple
from data_models import TowerDesign

# Import tower-type-specific base width ratio function
from pso_optimizer import get_base_width_ratio_for_tower_type


def validate_design_bounds(design: TowerDesign) -> List[str]:
    """
    Validate design parameters against hard bounds.
    
    Returns list of violation messages (empty if valid).
    Does NOT raise exceptions - violations are reported, not thrown.
    
    This is a defensive check to ensure optimizer outputs are within bounds.
    If violations are found, it indicates an optimizer bug.
    
    Args:
        design: TowerDesign to validate
        
    Returns:
        List of violation messages (empty if all bounds satisfied)
    """
    violations = []
    
    # Tower height bounds: 25-60 m
    if design.tower_height < 25.0:
        violations.append(f"Tower height ({design.tower_height:.2f} m) below minimum (25.0 m)")
    elif design.tower_height > 60.0:
        violations.append(f"Tower height ({design.tower_height:.2f} m) above maximum (60.0 m)")
    
    # Span length bounds: 250-450 m
    if design.span_length < 250.0:
        violations.append(f"Span length ({design.span_length:.2f} m) below minimum (250.0 m)")
    elif design.span_length > 450.0:
        violations.append(f"Span length ({design.span_length:.2f} m) above maximum (450.0 m)")
    
    # Footing length bounds: 3-8 m
    if design.footing_length < 3.0:
        violations.append(f"Footing length ({design.footing_length:.2f} m) below minimum (3.0 m)")
    elif design.footing_length > 8.0:
        violations.append(f"Footing length ({design.footing_length:.2f} m) above maximum (8.0 m)")
    
    # Footing width bounds: 3-8 m
    if design.footing_width < 3.0:
        violations.append(f"Footing width ({design.footing_width:.2f} m) below minimum (3.0 m)")
    elif design.footing_width > 8.0:
        violations.append(f"Footing width ({design.footing_width:.2f} m) above maximum (8.0 m)")
    
    # Footing depth bounds: 2-6 m
    if design.footing_depth < 2.0:
        violations.append(f"Footing depth ({design.footing_depth:.2f} m) below minimum (2.0 m)")
    elif design.footing_depth > 6.0:
        violations.append(f"Footing depth ({design.footing_depth:.2f} m) above maximum (6.0 m)")
    
    return violations


def check_geometry_constraint(design: TowerDesign) -> Tuple[bool, str]:
    """
    Check geometry-coupled base width constraint.
    
    This is a secondary sanity check that flags geometry corrections.
    Does NOT mark design as unsafe - it's an informational flag.
    
    Args:
        design: TowerDesign to check
        
    Returns:
        Tuple of (is_satisfied, message)
        - is_satisfied: True if constraint is satisfied
        - message: Description of constraint status (empty if satisfied)
    """
    # Get tower-type-specific base width ratio
    tower_type_ratio = get_base_width_ratio_for_tower_type(design.tower_type)
    min_base_width = design.tower_height * tower_type_ratio
    
    if design.base_width < min_base_width:
        return False, (
            f"geometry-corrected: base_width ({design.base_width:.2f} m) "
            f"was corrected to meet minimum ratio requirement "
            f"(height × {tower_type_ratio} = {min_base_width:.2f} m for {design.tower_type.value} tower)"
        )
    
    return True, ""




