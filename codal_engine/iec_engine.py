"""
IEC / BS Codal Engine.

Implements safety checks per:
- IEC 60826: Design Criteria of Overhead Transmission Lines
- BS EN 50341: Overhead Electrical Lines Exceeding AC 45 kV

This engine enforces IEC/BS compliance.
"""

from codal_engine.base import CodalEngine
from data_models import TowerDesign, OptimizationInputs, SafetyCheckResult


class IECEngine(CodalEngine):
    """
    IEC / BS codal engine.
    
    Enforces IEC 60826 and BS EN 50341 requirements.
    """
    
    def __init__(self):
        super().__init__("IEC / BS (IEC 60826, BS EN 50341)")
    
    def is_design_safe(
        self,
        design: TowerDesign,
        inputs: OptimizationInputs
    ) -> SafetyCheckResult:
        """
        Check design safety per IEC/BS standards.
        
        Performs checks in order:
        1. Shallow foundation feasibility
        2. Structural feasibility
        3. Electrical clearance (IEC 60826)
        4. Wind loading (IEC 60826)
        5. Foundation design (BS EN 50341)
        """
        violations = []
        
        # Check 1: Shallow foundation feasibility
        is_feasible, msg = self._check_shallow_foundation_feasibility(design, inputs)
        if not is_feasible:
            violations.append(f"IEC Foundation Check: {msg}")
        
        # Check 2: Structural feasibility
        is_feasible, msg = self._check_structural_feasibility(design, inputs)
        if not is_feasible:
            violations.append(f"IEC Structural Check: {msg}")
        
        # Check 3: Electrical clearance (IEC 60826)
        is_feasible, msg = self._check_electrical_clearance(design, inputs)
        if not is_feasible:
            violations.append(f"IEC 60826 Clearance Check: {msg}")
        
        # Check 4: Wind exposure (IEC 60826)
        is_feasible, msg = self._check_wind_exposure(design, inputs)
        if not is_feasible:
            violations.append(f"IEC 60826 Wind Check: {msg}")
        
        # Check 5: IEC-specific foundation requirements
        # IEC requires minimum foundation depth of 2.0 m for shallow foundations
        if design.footing_depth < 2.0:
            violations.append(
                f"IEC Foundation Depth: Minimum depth 2.0 m required. "
                f"Design has {design.footing_depth:.2f} m"
            )
        
        # Check 6: IEC-specific base width ratio
        # IEC 60826 recommends base width between 0.25H and 0.35H
        height_ratio_min = design.tower_height * 0.25
        height_ratio_max = design.tower_height * 0.35
        if design.base_width < height_ratio_min or design.base_width > height_ratio_max:
            violations.append(
                f"IEC 60826 Base Width: Must be between 0.25H ({height_ratio_min:.2f} m) "
                f"and 0.35H ({height_ratio_max:.2f} m). Design has {design.base_width:.2f} m"
            )
        
        # Check 7: IEC span length requirements
        # Span must be reasonable for tower height
        max_span_ratio = 10.0  # Maximum span/height ratio
        span_ratio = design.span_length / design.tower_height
        if span_ratio > max_span_ratio:
            violations.append(
                f"IEC 60826 Span Ratio: Span/height ratio ({span_ratio:.2f}) exceeds "
                f"maximum allowed ({max_span_ratio})"
            )
        
        return SafetyCheckResult(
            is_safe=len(violations) == 0,
            violations=violations
        )

