"""
Design validation utilities.

This module provides validation functions that return violation lists
instead of raising exceptions. This ensures the API always returns
structured responses, never crashes.
"""

from typing import List
from data_models import TowerDesign


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



