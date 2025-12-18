"""
Base Codal Engine Abstract Class.

This defines the interface that all codal engines must implement.
The codal engine is responsible ONLY for safety checks - no optimization,
no cost considerations.
"""

from abc import ABC, abstractmethod
from typing import Tuple
from data_models import TowerDesign, OptimizationInputs, SafetyCheckResult, FoundationType


class CodalEngine(ABC):
    """
    Abstract base class for codal rule engines.
    
    Each implementation enforces a specific design standard:
    - IS (Indian Standards)
    - IEC (International Electrotechnical Commission)
    - Eurocode (European Standards)
    - ASCE (American Society of Civil Engineers)
    
    RESPONSIBILITIES:
    - Determine if a design is safe (PASS / FAIL)
    - Enforce code compliance
    - Report violations
    
    NOT RESPONSIBLE FOR:
    - Optimization
    - Cost calculations
    - Design generation
    """
    
    def __init__(self, standard_name: str):
        """
        Initialize codal engine.
        
        Args:
            standard_name: Human-readable name of the design standard
        """
        self.standard_name = standard_name
    
    @abstractmethod
    def is_design_safe(
        self,
        design: TowerDesign,
        inputs: OptimizationInputs
    ) -> SafetyCheckResult:
        """
        Check if a design is safe according to the governing code.
        
        This is the PRIMARY method of the codal engine.
        It performs all safety checks and returns a binary result.
        
        Args:
            design: TowerDesign to evaluate
            inputs: OptimizationInputs containing project context
            
        Returns:
            SafetyCheckResult with:
            - is_safe: True if design passes all checks, False otherwise
            - violations: List of code violation descriptions (empty if safe)
            
        Note:
            This method is deterministic and has no side effects.
            It does NOT modify the design or inputs.
        """
        pass
    
    def _check_shallow_foundation_feasibility(
        self,
        design: TowerDesign,
        inputs: OptimizationInputs
    ) -> Tuple[bool, str]:
        """
        Check if shallow foundation is feasible for given soil conditions.
        
        This is a common check across all codes.
        Designs requiring piles MUST be rejected.
        
        Uses deterministic soil-based sanity limits for footing dimensions.
        
        Args:
            design: TowerDesign to check
            inputs: OptimizationInputs with soil category
            
        Returns:
            Tuple of (is_feasible, violation_message)
        """
        # Reject if foundation type is not shallow
        if design.foundation_type not in [
            FoundationType.PAD_FOOTING,
            FoundationType.CHIMNEY_FOOTING
        ]:
            return False, f"Only shallow foundations are supported. Found: {design.foundation_type}"
        
        # Soil-based shallow foundation sanity limits
        # These are deterministic filters, not final design checks
        soil_bounds = {
            "soft": {
                "footing_length": (5.0, 8.0),
                "footing_width": (5.0, 8.0),
                "footing_depth": (4.0, float('inf')),
            },
            "medium": {
                "footing_length": (3.5, 6.5),
                "footing_width": (3.5, 6.5),
                "footing_depth": (2.5, float('inf')),
            },
            "hard": {
                "footing_length": (3.0, 5.5),
                "footing_width": (3.0, 5.5),
                "footing_depth": (2.0, float('inf')),
            },
            "rock": {
                "footing_length": (3.0, 5.5),
                "footing_width": (3.0, 5.5),
                "footing_depth": (2.0, float('inf')),
            },
        }
        
        soil_type = inputs.soil_category.value
        if soil_type not in soil_bounds:
            return False, f"Unknown soil category: {soil_type}"
        
        bounds = soil_bounds[soil_type]
        
        # Check footing length
        if design.footing_length < bounds["footing_length"][0]:
            return False, (
                f"Soil category '{soil_type}' requires minimum footing length "
                f"of {bounds['footing_length'][0]} m. Design has {design.footing_length:.2f} m"
            )
        if design.footing_length > bounds["footing_length"][1]:
            return False, (
                f"Soil category '{soil_type}' requires maximum footing length "
                f"of {bounds['footing_length'][1]} m. Design has {design.footing_length:.2f} m"
            )
        
        # Check footing width
        if design.footing_width < bounds["footing_width"][0]:
            return False, (
                f"Soil category '{soil_type}' requires minimum footing width "
                f"of {bounds['footing_width'][0]} m. Design has {design.footing_width:.2f} m"
            )
        if design.footing_width > bounds["footing_width"][1]:
            return False, (
                f"Soil category '{soil_type}' requires maximum footing width "
                f"of {bounds['footing_width'][1]} m. Design has {design.footing_width:.2f} m"
            )
        
        # Check footing depth
        if design.footing_depth < bounds["footing_depth"][0]:
            return False, (
                f"Soil category '{soil_type}' requires minimum footing depth "
                f"of {bounds['footing_depth'][0]} m. Design has {design.footing_depth:.2f} m"
            )
        
        return True, ""
    
    def _check_structural_feasibility(
        self,
        design: TowerDesign,
        inputs: OptimizationInputs
    ) -> Tuple[bool, str]:
        """
        Basic structural feasibility checks common across codes.
        
        Args:
            design: TowerDesign to check
            inputs: OptimizationInputs with voltage level
            
        Returns:
            Tuple of (is_feasible, violation_message)
        """
        # Check 1: Tower type vs span consistency (HARD CONSTRAINT)
        is_feasible, msg = self._check_tower_type_span_consistency(design, inputs)
        if not is_feasible:
            return False, msg
        
        # Check 2: Early geometric coupling check: span-height ratio
        span_height_ratio = design.span_length / design.tower_height
        max_span_height_ratio = 10.0
        if span_height_ratio > max_span_height_ratio:
            return False, (
                f"Span-height ratio ({span_height_ratio:.2f}) exceeds "
                f"maximum allowed ({max_span_height_ratio}). "
                f"Span: {design.span_length:.2f} m, Height: {design.tower_height:.2f} m"
            )
        
        # Check 3: Aspect ratio (height to base width)
        aspect_ratio = design.tower_height / design.base_width
        if aspect_ratio > 15.0:
            return False, (
                f"Aspect ratio (H/B) too high: {aspect_ratio:.2f}. "
                f"Maximum allowed: 15.0"
            )
        if aspect_ratio < 2.0:
            return False, (
                f"Aspect ratio (H/B) too low: {aspect_ratio:.2f}. "
                f"Minimum required: 2.0"
            )
        
        return True, ""
    
    def _check_tower_type_span_consistency(
        self,
        design: TowerDesign,
        inputs: OptimizationInputs
    ) -> Tuple[bool, str]:
        """
        Check if span length is consistent with tower type.
        
        This is a HARD FEASIBILITY CONSTRAINT.
        Designs violating this rule are rejected as infeasible.
        
        Args:
            design: TowerDesign to check
            inputs: OptimizationInputs with voltage level
            
        Returns:
            Tuple of (is_feasible, violation_message)
        """
        from data_models import TowerType
        
        # Typical span by voltage level (standard suspension spans in flat terrain)
        typical_spans = {
            132: 250.0,
            220: 300.0,
            400: 400.0,
            765: 450.0,
            900: 500.0,
        }
        
        # Find typical span for voltage level
        voltage = inputs.voltage_level
        typical_span = 250.0  # Default for lower voltages
        for v_level, span in sorted(typical_spans.items()):
            if voltage >= v_level:
                typical_span = span
        
        tower_type = design.tower_type.value
        span = design.span_length
        
        # Rule 1: SUSPENSION TOWERS
        # Allowed range: 0.6 × S_typ ≤ span ≤ 1.1 × S_typ
        if tower_type == "suspension":
            min_span = 0.6 * typical_span
            max_span = 1.1 * typical_span
            
            if span < min_span:
                return False, (
                    f"Span length inconsistent with tower type: "
                    f"Suspension tower requires span ≥ {min_span:.0f} m "
                    f"(0.6 × typical span of {typical_span:.0f} m for {voltage} kV). "
                    f"Design has {span:.2f} m"
                )
            
            if span > max_span:
                return False, (
                    f"Span length inconsistent with tower type: "
                    f"Suspension tower requires span ≤ {max_span:.0f} m "
                    f"(1.1 × typical span of {typical_span:.0f} m for {voltage} kV). "
                    f"Design has {span:.2f} m"
                )
        
        # Rule 2: TENSION / DEAD-END TOWERS
        # Allowed range: span ≥ 0.75 × S_typ
        elif tower_type in ["tension", "dead_end"]:
            min_span = 0.75 * typical_span
            
            if span < min_span:
                return False, (
                    f"Span length inconsistent with tower type: "
                    f"{tower_type.capitalize()} tower requires span ≥ {min_span:.0f} m "
                    f"(0.75 × typical span of {typical_span:.0f} m for {voltage} kV). "
                    f"Design has {span:.2f} m"
                )
        
        # Rule 3: ANGLE TOWERS
        # Angle towers can handle similar spans to suspension towers
        # Use same bounds as suspension for conservatism
        elif tower_type == "angle":
            min_span = 0.6 * typical_span
            max_span = 1.1 * typical_span
            
            if span < min_span:
                return False, (
                    f"Span length inconsistent with tower type: "
                    f"Angle tower requires span ≥ {min_span:.0f} m "
                    f"(0.6 × typical span of {typical_span:.0f} m for {voltage} kV). "
                    f"Design has {span:.2f} m"
                )
            
            if span > max_span:
                return False, (
                    f"Span length inconsistent with tower type: "
                    f"Angle tower requires span ≤ {max_span:.0f} m "
                    f"(1.1 × typical span of {typical_span:.0f} m for {voltage} kV). "
                    f"Design has {span:.2f} m"
                )
        
        return True, ""
    
    def _check_electrical_clearance(
        self,
        design: TowerDesign,
        inputs: OptimizationInputs
    ) -> Tuple[bool, str]:
        """
        Check electrical clearance requirements under maximum sag conditions.
        
        This is a HARD FAILURE check. Designs with insufficient clearance
        are rejected as UNSAFE.
        
        Args:
            design: TowerDesign to check
            inputs: OptimizationInputs with voltage level
            
        Returns:
            Tuple of (is_feasible, violation_message)
            Returns False if clearance violation (hard failure)
        """
        # Required minimum clearance by voltage level (ground clearance)
        required_clearance_by_voltage = {
            132: 6.1,   # m
            220: 7.0,   # m
            400: 8.5,   # m
            765: 11.0,  # m
            900: 12.5,  # m
        }
        
        # Find required clearance for voltage level
        voltage = inputs.voltage_level
        required_clearance = 6.1  # Default for lower voltages
        for v_level, clearance in sorted(required_clearance_by_voltage.items()):
            if voltage >= v_level:
                required_clearance = clearance
        
        # Sag allowance based on voltage and span length
        sag_allowance = self._get_sag_allowance(voltage, design.span_length)
        
        # Actual clearance = tower height - sag allowance
        # Conservative: assumes conductor attachment at tower top
        actual_clearance = design.tower_height - sag_allowance
        
        # Check if clearance violation (HARD FAILURE)
        if actual_clearance < required_clearance:
            return False, (
                f"Electrical clearance violation under maximum sag conditions. "
                f"Required clearance: {required_clearance:.2f} m, "
                f"Actual clearance: {actual_clearance:.2f} m "
                f"(tower height: {design.tower_height:.2f} m - sag allowance: {sag_allowance:.2f} m)"
            )
        
        return True, ""
    
    def _get_sag_allowance(self, voltage: float, span_length: float) -> float:
        """
        Get conservative sag allowance for clearance calculation.
        
        This is a simplified proxy for maximum sag under worst-case conditions
        (high temperature, ice loading, wind deflection).
        
        Args:
            voltage: Voltage level in kV
            span_length: Span length in meters
            
        Returns:
            Sag allowance in meters
        """
        # Sag allowance lookup by voltage and span
        # Conservative values accounting for maximum sag conditions
        
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
    
    def _get_clearance_margin(
        self,
        design: TowerDesign,
        inputs: OptimizationInputs
    ) -> Tuple[float, float]:
        """
        Calculate clearance margin for warning purposes.
        
        This is used by the constructability warning layer, NOT for rejection.
        
        Args:
            design: TowerDesign to check
            inputs: OptimizationInputs with voltage level
            
        Returns:
            Tuple of (clearance_margin, warning_threshold)
        """
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
        
        # Sag allowance
        sag_allowance = self._get_sag_allowance(voltage, design.span_length)
        
        # Actual clearance
        actual_clearance = design.tower_height - sag_allowance
        
        # Clearance margin
        clearance_margin = actual_clearance - required_clearance
        
        # Warning threshold (10% of required clearance)
        warning_threshold = 0.10 * required_clearance
        
        return clearance_margin, warning_threshold
    
    def _check_wind_exposure(
        self,
        design: TowerDesign,
        inputs: OptimizationInputs
    ) -> Tuple[bool, str]:
        """
        Basic wind exposure sanity checks.
        
        Args:
            design: TowerDesign to check
            inputs: OptimizationInputs with wind zone
            
        Returns:
            Tuple of (is_feasible, violation_message)
        """
        # Higher wind zones require more robust designs
        wind_zone_multiplier = {
            "zone_1": 1.0,
            "zone_2": 1.1,
            "zone_3": 1.2,
            "zone_4": 1.3,
        }
        
        multiplier = wind_zone_multiplier.get(inputs.wind_zone.value, 1.0)
        min_base_width = design.tower_height * 0.25 * multiplier
        
        if design.base_width < min_base_width:
            return False, (
                f"Base width ({design.base_width:.2f} m) insufficient "
                f"for wind zone {inputs.wind_zone.value}. "
                f"Minimum required: {min_base_width:.2f} m"
            )
        
        return True, ""

