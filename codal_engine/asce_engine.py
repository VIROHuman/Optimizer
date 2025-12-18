"""
ASCE / AISC / IEEE Codal Engine.

Implements safety checks per:
- ASCE 10: Design of Latticed Steel Transmission Structures
- AISC 360: Specification for Structural Steel Buildings
- IEEE 691: IEEE Guide for Transmission Structure Foundation Design and Testing

This engine enforces ASCE/AISC/IEEE compliance.
"""

from codal_engine.base import CodalEngine
from data_models import TowerDesign, OptimizationInputs, SafetyCheckResult


class ASCEEngine(CodalEngine):
    """
    ASCE / AISC / IEEE codal engine.
    
    Enforces ASCE 10, AISC 360, and IEEE 691 requirements.
    """
    
    def __init__(self):
        super().__init__("ASCE / AISC / IEEE (ASCE 10, AISC 360, IEEE 691)")
    
    def is_design_safe(
        self,
        design: TowerDesign,
        inputs: OptimizationInputs
    ) -> SafetyCheckResult:
        """
        Check design safety per ASCE/AISC/IEEE standards.
        
        Performs checks in order:
        1. Shallow foundation feasibility
        2. Structural feasibility
        3. Electrical clearance (ASCE 10)
        4. Wind loading (ASCE 10)
        5. Foundation design (IEEE 691)
        """
        violations = []
        
        # Check 1: Shallow foundation feasibility
        is_feasible, msg = self._check_shallow_foundation_feasibility(design, inputs)
        if not is_feasible:
            violations.append(f"ASCE Foundation Check: {msg}")
        
        # Check 2: Structural feasibility
        is_feasible, msg = self._check_structural_feasibility(design, inputs)
        if not is_feasible:
            violations.append(f"ASCE Structural Check: {msg}")
        
        # Check 3: Electrical clearance (ASCE 10)
        is_feasible, msg = self._check_electrical_clearance(design, inputs)
        if not is_feasible:
            violations.append(f"ASCE 10 Clearance Check: {msg}")
        
        # Check 4: Wind exposure (ASCE 10)
        is_feasible, msg = self._check_wind_exposure(design, inputs)
        if not is_feasible:
            violations.append(f"ASCE 10 Wind Check: {msg}")
        
        # Check 5: ASCE-specific foundation depth (IEEE 691)
        # IEEE 691 requires minimum foundation depth based on frost and soil
        min_depth_by_soil = {
            "soft": 3.0,
            "medium": 2.5,
            "hard": 2.0,
            "rock": 2.0,
        }
        min_depth = min_depth_by_soil.get(inputs.soil_category.value, 2.5)
        if design.footing_depth < min_depth:
            violations.append(
                f"IEEE 691 Foundation Depth: Minimum depth {min_depth} m required "
                f"for {inputs.soil_category.value} soil. Design has {design.footing_depth:.2f} m"
            )
        
        # Check 6: ASCE-specific base width ratio
        # ASCE 10 recommends base width between 0.25H and 0.40H
        height_ratio_min = design.tower_height * 0.25
        height_ratio_max = design.tower_height * 0.40
        if design.base_width < height_ratio_min or design.base_width > height_ratio_max:
            violations.append(
                f"ASCE 10 Base Width: Must be between 0.25H ({height_ratio_min:.2f} m) "
                f"and 0.40H ({height_ratio_max:.2f} m). Design has {design.base_width:.2f} m"
            )
        
        # Check 7: ASCE structural stability (AISC 360)
        # Check aspect ratio for stability
        aspect_ratio = design.tower_height / design.base_width
        max_aspect_ratio = 14.0
        if aspect_ratio > max_aspect_ratio:
            violations.append(
                f"AISC 360 Aspect Ratio: Aspect ratio ({aspect_ratio:.2f}) exceeds "
                f"maximum allowed ({max_aspect_ratio})"
            )
        
        # Check 8: ASCE span requirements
        # Span must be reasonable for tower type
        if design.tower_type.value == "suspension":
            max_span = 400.0
            if design.span_length > max_span:
                violations.append(
                    f"ASCE 10 Span Length: Suspension tower span ({design.span_length:.2f} m) "
                    f"exceeds maximum ({max_span} m)"
                )
        
        return SafetyCheckResult(
            is_safe=len(violations) == 0,
            violations=violations
        )

