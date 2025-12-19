"""
Constructability & Practicality Warning Engine.

This module provides advisory warnings for transmission tower designs
that are structurally safe but may have constructability concerns.

CRITICAL PRINCIPLES:
- NEVER auto-reject structurally safe designs
- ONLY flag warnings (not failures)
- Be region-aware but conservative
- Reflect real-world EPC construction practices

This layer bridges the gap between "structurally safe" and "practically buildable".
"""

from typing import List
from data_models import (
    TowerDesign, OptimizationInputs, WindZone, SoilCategory
)
from cost_engine import calculate_cost


class ConstructabilityWarning:
    """Represents a single constructability warning."""
    
    def __init__(self, message: str, severity: str = "advisory"):
        """
        Initialize warning.
        
        Args:
            message: Human-readable warning message
            severity: "advisory" or "caution" (for future use)
        """
        self.message = message
        self.severity = severity
    
    def __str__(self):
        return self.message
    
    def to_dict(self) -> dict:
        """
        Convert warning to JSON-serializable dictionary.
        
        Returns:
            Dictionary with type, message, and severity fields
        """
        return {
            "type": "constructability",
            "message": self.message,
            "severity": self.severity,
        }


def check_constructability(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> List[ConstructabilityWarning]:
    """
    Check design for constructability and practicality warnings.
    
    This function does NOT reject designs. It only flags warnings.
    
    Args:
        design: TowerDesign to check
        inputs: OptimizationInputs with project context
        
    Returns:
        List of ConstructabilityWarning objects (empty if no warnings)
    """
    warnings = []
    
    # Check 1: Foundation depth (shallow footings)
    warnings.extend(_check_foundation_depth(design, inputs))
    
    # Check 2: Footing size (constructability)
    warnings.extend(_check_footing_size(design))
    
    # Check 3: Low clearance margin (EHV risk)
    warnings.extend(_check_clearance_margin(design, inputs))
    
    # Check 4: Span conservatism
    warnings.extend(_check_span_conservatism(design, inputs))
    
    # Check 5: High wind + soft soil combination
    warnings.extend(_check_wind_soil_combination(design, inputs))
    
    # Check 6: Base width practicality
    warnings.extend(_check_base_width_practicality(design))
    
    # Check 7: Cost anomaly check
    warnings.extend(_check_cost_anomaly(design, inputs))
    
    # Check 8: Foundation type limitation
    warnings.extend(_check_foundation_type_limitation(design, inputs))
    
    return warnings


def _check_foundation_depth(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> List[ConstructabilityWarning]:
    """Check 1: Foundation depth warning."""
    warnings = []
    
    if design.footing_depth > 3.5:
        warning_msg = (
            f"Deep shallow foundation detected ({design.footing_depth:.2f} m > 3.5 m). "
            f"May require groundwater assessment, shoring, or alternate foundation type."
        )
        
        if inputs.soil_category == SoilCategory.SOFT:
            warning_msg += " Soft soil + deep footing increases excavation risk."
        
        warnings.append(ConstructabilityWarning(warning_msg))
    
    return warnings


def _check_footing_size(design: TowerDesign) -> List[ConstructabilityWarning]:
    """Check 2: Footing size constructability warning."""
    warnings = []
    
    if design.footing_length > 6.5 or design.footing_width > 6.5:
        warning_msg = (
            f"Large shallow footing footprint "
            f"({design.footing_length:.2f} m × {design.footing_width:.2f} m). "
            f"Check excavation stability, working space, and concreting logistics."
        )
        warnings.append(ConstructabilityWarning(warning_msg))
    
    return warnings


def _check_clearance_margin(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> List[ConstructabilityWarning]:
    """Check 3: Low clearance margin (EHV risk)."""
    warnings = []
    
    try:
        # Calculate clearance margin using same logic as codal engine
        # Required minimum clearance by voltage level
        required_clearance_by_voltage = {
            132: 6.1,
            220: 7.0,
            400: 8.5,
            765: 11.0,
            900: 12.5,
        }
        
        voltage = inputs.voltage_level
        required_clearance = 6.1
        for v_level, clearance in sorted(required_clearance_by_voltage.items()):
            if voltage >= v_level:
                required_clearance = clearance
        
        # Sag allowance (same as codal engine)
        sag_allowance = _get_sag_allowance_for_warning(voltage, design.span_length)
        
        # Actual clearance
        actual_clearance = design.tower_height - sag_allowance
        
        # Clearance margin
        clearance_margin = actual_clearance - required_clearance
        
        # Warning threshold (10% of required clearance)
        warning_threshold = 0.10 * required_clearance
        
        # Check if clearance margin is below warning threshold
        if clearance_margin < warning_threshold:
            warning_msg = (
                f"Clearance margin is low under maximum sag and wind conditions "
                f"(margin: {clearance_margin:.2f} m < threshold: {warning_threshold:.2f} m). "
                f"Detailed sag-tension analysis recommended."
            )
            warnings.append(ConstructabilityWarning(warning_msg))
    except Exception:
        # If clearance calculation fails, skip this check
        pass
    
    return warnings


def _get_sag_allowance_for_warning(voltage: float, span_length: float) -> float:
    """
    Get conservative sag allowance for clearance calculation (same as codal engine).
    
    Args:
        voltage: Voltage level in kV
        span_length: Span length in meters
        
    Returns:
        Sag allowance in meters
    """
    if voltage <= 132:
        if span_length <= 300:
            return 6.0
        elif span_length <= 400:
            return 7.0
        else:
            return 8.0
    elif voltage <= 220:
        if span_length <= 300:
            return 7.0
        elif span_length <= 400:
            return 8.5
        else:
            return 10.0
    elif voltage <= 400:
        if span_length <= 300:
            return 8.0
        elif span_length <= 400:
            return 9.5
        else:
            return 11.0
    elif voltage <= 765:
        if span_length <= 400:
            return 10.0
        elif span_length <= 450:
            return 11.5
        else:
            return 13.0
    else:  # 900 kV
        if span_length <= 400:
            return 11.0
        elif span_length <= 450:
            return 12.5
        else:
            return 14.5


def _check_span_conservatism(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> List[ConstructabilityWarning]:
    """Check 4: Span conservatism (informational)."""
    warnings = []
    
    # Typical spans by voltage level (approximate)
    typical_spans = {
        132: 300.0,
        220: 350.0,
        400: 400.0,
        765: 450.0,
        900: 450.0,
    }
    
    # Find typical span for voltage level
    voltage = inputs.voltage_level
    typical_span = 350.0  # Default
    for v_level, span in sorted(typical_spans.items()):
        if voltage >= v_level:
            typical_span = span
    
    # Check if span is less than 80% of typical
    threshold = typical_span * 0.8
    if design.span_length < threshold:
        warning_msg = (
            f"Short span selected ({design.span_length:.2f} m vs typical ~{typical_span:.0f} m "
            f"for {voltage} kV). May increase number of towers and total project cost."
        )
        warnings.append(ConstructabilityWarning(warning_msg))
    
    return warnings


def _check_wind_soil_combination(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> List[ConstructabilityWarning]:
    """Check 5: High wind + soft soil combination."""
    warnings = []
    
    # Check if wind zone is zone_3 or zone_4
    high_wind = inputs.wind_zone in [WindZone.ZONE_3, WindZone.ZONE_4]
    soft_soil = inputs.soil_category == SoilCategory.SOFT
    
    if high_wind and soft_soil:
        warning_msg = (
            f"High wind ({inputs.wind_zone.value}) and soft soil combination. "
            f"Foundation uplift and overturning sensitivity expected."
        )
        warnings.append(ConstructabilityWarning(warning_msg))
    
    return warnings


def _check_base_width_practicality(design: TowerDesign) -> List[ConstructabilityWarning]:
    """Check 6: Base width practicality."""
    warnings = []
    
    min_base_width_ratio = 0.25
    actual_ratio = design.base_width / design.tower_height
    
    if actual_ratio < min_base_width_ratio:
        warning_msg = (
            f"Compact tower base relative to height "
            f"(base_width/height = {actual_ratio:.3f} < {min_base_width_ratio}). "
            f"Check erection stability and leg force concentration."
        )
        warnings.append(ConstructabilityWarning(warning_msg))
    
    return warnings


def _check_cost_anomaly(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> List[ConstructabilityWarning]:
    """Check 7: Cost anomaly check (advisory)."""
    warnings = []
    
    try:
        total_cost = calculate_cost(design, inputs)
        
        if total_cost < 250000.0:
            warning_msg = (
                f"Estimated cost (${total_cost:,.2f} USD) below typical per-tower range "
                f"($250,000 - $2,000,000 USD). "
                f"Verify geometry, cost assumptions, and regional multipliers."
            )
            warnings.append(ConstructabilityWarning(warning_msg))
        
        if total_cost > 2000000.0:
            warning_msg = (
                f"Estimated cost (${total_cost:,.2f} USD) exceeds typical per-tower range "
                f"($250,000 - $2,000,000 USD). "
                f"Verify geometry, cost assumptions, and regional multipliers."
            )
            warnings.append(ConstructabilityWarning(warning_msg))
    except Exception:
        # If cost calculation fails, skip this check
        pass
    
    return warnings


def _check_foundation_type_limitation(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> List[ConstructabilityWarning]:
    """Check 8: Foundation type limitation."""
    warnings = []
    
    from data_models import FoundationType
    
    # Only check pad footings
    if design.foundation_type != FoundationType.PAD_FOOTING:
        return warnings
    
    # Check conditions
    deep_footing = design.footing_depth > 4.0
    very_high_wind = inputs.wind_zone == WindZone.ZONE_4
    soft_soil = inputs.soil_category == SoilCategory.SOFT
    
    if deep_footing or very_high_wind or soft_soil:
        conditions = []
        if deep_footing:
            conditions.append(f"deep footing ({design.footing_depth:.2f} m > 4.0 m)")
        if very_high_wind:
            conditions.append(f"very high wind ({inputs.wind_zone.value})")
        if soft_soil:
            conditions.append("soft soil")
        
        condition_str = ", ".join(conditions)
        warning_msg = (
            f"Shallow foundation at practical limit ({condition_str}). "
            f"Alternate foundation systems (pile / anchor) may be required."
        )
        warnings.append(ConstructabilityWarning(warning_msg))
    
    return warnings


def format_warnings(warnings: List[ConstructabilityWarning]) -> str:
    """
    Format warnings for display.
    
    Args:
        warnings: List of ConstructabilityWarning objects
        
    Returns:
        Formatted string for display
    """
    if not warnings:
        return "No constructability warnings identified."
    
    lines = []
    lines.append("=" * 70)
    lines.append("CONSTRUCTABILITY & PRACTICALITY WARNINGS")
    lines.append("=" * 70)
    lines.append("")
    
    for i, warning in enumerate(warnings, 1):
        lines.append(f"{i}. {warning.message}")
        lines.append("")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)

