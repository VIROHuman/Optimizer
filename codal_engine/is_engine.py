"""
Indian Standards (IS) Codal Engine.

Implements safety checks per:
- IS 802: Code of Practice for Use of Structural Steel in Overhead Transmission Line Towers
- IS 875: Code of Practice for Design Loads
- IS 456: Plain and Reinforced Concrete Code

This engine enforces Indian Standards compliance.
"""

from codal_engine.base import CodalEngine
from data_models import TowerDesign, OptimizationInputs, SafetyCheckResult


class ISEngine(CodalEngine):
    """
    Indian Standards codal engine.
    
    Enforces IS 802, IS 875, and IS 456 requirements.
    """
    
    def __init__(self):
        super().__init__("Indian Standards (IS 802, IS 875, IS 456)")
    
    def is_design_safe(
        self,
        design: TowerDesign,
        inputs: OptimizationInputs
    ) -> SafetyCheckResult:
        """
        Check design safety per Indian Standards.
        
        Performs checks in order:
        1. Shallow foundation feasibility
        2. Structural feasibility
        3. Electrical clearance (IS 802)
        4. Wind loading (IS 875)
        5. Foundation design (IS 456)
        """
        violations = []
        
        # Check 1: Shallow foundation feasibility
        is_feasible, msg = self._check_shallow_foundation_feasibility(design, inputs)
        if not is_feasible:
            violations.append(f"IS Foundation Check: {msg}")
        
        # Check 2: Structural feasibility
        is_feasible, msg = self._check_structural_feasibility(design, inputs)
        if not is_feasible:
            violations.append(f"IS Structural Check: {msg}")
        
        # Check 3: Electrical clearance (IS 802)
        is_feasible, msg = self._check_electrical_clearance(design, inputs)
        if not is_feasible:
            violations.append(f"IS 802 Clearance Check: {msg}")
        
        # Check 4: Wind exposure (IS 875)
        is_feasible, msg = self._check_wind_exposure(design, inputs)
        if not is_feasible:
            violations.append(f"IS 875 Wind Check: {msg}")
        
        # Check 5: IS-specific foundation depth requirements
        # IS 456 requires minimum foundation depth based on soil
        min_depth_by_soil = {
            "soft": 3.0,
            "medium": 2.5,
            "hard": 2.0,
            "rock": 2.0,
        }
        min_depth = min_depth_by_soil.get(inputs.soil_category.value, 2.5)
        if design.footing_depth < min_depth:
            violations.append(
                f"IS 456 Foundation Depth: Minimum depth {min_depth} m required "
                f"for {inputs.soil_category.value} soil. Design has {design.footing_depth:.2f} m"
            )
        
        # Check 6: IS-specific base width ratio
        # IS 802 recommends base width between 0.25H and 0.40H
        height_ratio_min = design.tower_height * 0.25
        height_ratio_max = design.tower_height * 0.40
        if design.base_width < height_ratio_min or design.base_width > height_ratio_max:
            violations.append(
                f"IS 802 Base Width: Must be between 0.25H ({height_ratio_min:.2f} m) "
                f"and 0.40H ({height_ratio_max:.2f} m). Design has {design.base_width:.2f} m"
            )
        
        return SafetyCheckResult(
            is_safe=len(violations) == 0,
            violations=violations
        )

