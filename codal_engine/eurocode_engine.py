"""
Eurocode Codal Engine.

Implements safety checks per:
- EN 50341: Overhead Electrical Lines Exceeding AC 45 kV
- EN 1993: Eurocode 3 - Design of Steel Structures
- EN 1997: Eurocode 7 - Geotechnical Design

This engine enforces Eurocode compliance.
"""

from codal_engine.base import CodalEngine
from data_models import TowerDesign, OptimizationInputs, SafetyCheckResult


class EurocodeEngine(CodalEngine):
    """
    Eurocode codal engine.
    
    Enforces EN 50341, EN 1993, and EN 1997 requirements.
    """
    
    def __init__(self):
        super().__init__("Eurocode (EN 50341, EN 1993, EN 1997)")
    
    def is_design_safe(
        self,
        design: TowerDesign,
        inputs: OptimizationInputs
    ) -> SafetyCheckResult:
        """
        Check design safety per Eurocode standards.
        
        Performs checks in order:
        1. Shallow foundation feasibility
        2. Structural feasibility
        3. Electrical clearance (EN 50341)
        4. Wind loading (EN 50341)
        5. Foundation design (EN 1997)
        """
        violations = []
        
        # Check 1: Shallow foundation feasibility
        is_feasible, msg = self._check_shallow_foundation_feasibility(design, inputs)
        if not is_feasible:
            violations.append(f"Eurocode Foundation Check: {msg}")
        
        # Check 2: Structural feasibility
        is_feasible, msg = self._check_structural_feasibility(design, inputs)
        if not is_feasible:
            violations.append(f"Eurocode Structural Check: {msg}")
        
        # Check 3: Electrical clearance (EN 50341)
        is_feasible, msg = self._check_electrical_clearance(design, inputs)
        if not is_feasible:
            violations.append(f"EN 50341 Clearance Check: {msg}")
        
        # Check 4: Wind exposure (EN 50341)
        is_feasible, msg = self._check_wind_exposure(design, inputs)
        if not is_feasible:
            violations.append(f"EN 50341 Wind Check: {msg}")
        
        # Check 5: Eurocode-specific foundation depth (EN 1997)
        # EN 1997 requires minimum foundation depth based on frost depth and soil
        min_depth_by_soil = {
            "soft": 2.5,
            "medium": 2.0,
            "hard": 1.5,
            "rock": 1.5,
        }
        min_depth = min_depth_by_soil.get(inputs.soil_category.value, 2.0)
        if design.footing_depth < min_depth:
            violations.append(
                f"EN 1997 Foundation Depth: Minimum depth {min_depth} m required "
                f"for {inputs.soil_category.value} soil. Design has {design.footing_depth:.2f} m"
            )
        
        # Check 6: Eurocode-specific base width ratio
        # EN 50341 recommends base width between 0.25H and 0.40H
        height_ratio_min = design.tower_height * 0.25
        height_ratio_max = design.tower_height * 0.40
        if design.base_width < height_ratio_min or design.base_width > height_ratio_max:
            violations.append(
                f"EN 50341 Base Width: Must be between 0.25H ({height_ratio_min:.2f} m) "
                f"and 0.40H ({height_ratio_max:.2f} m). Design has {design.base_width:.2f} m"
            )
        
        # Check 7: Eurocode structural stability (EN 1993)
        # Check slenderness ratio
        slenderness = design.tower_height / design.base_width
        max_slenderness = 12.0
        if slenderness > max_slenderness:
            violations.append(
                f"EN 1993 Slenderness: Slenderness ratio ({slenderness:.2f}) exceeds "
                f"maximum allowed ({max_slenderness})"
            )
        
        return SafetyCheckResult(
            is_safe=len(violations) == 0,
            violations=violations
        )

