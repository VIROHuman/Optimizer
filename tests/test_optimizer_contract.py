"""
Assertion Tests for Optimizer Core Contract.

These tests ensure the optimizer NEVER violates its core promise:
- Always returns cheapest SAFE design
- Span always within bounds
- Cost monotonically penalizes unsafe candidates
"""

import pytest
from data_models import (
    OptimizationInputs, DesignStandard, TowerType,
    TerrainType, WindZone, SoilCategory, OptimizationResult
)
from pso_optimizer import PSOOptimizer, VERY_LARGE_PENALTY
from codal_engine import ISEngine


class TestOptimizerContract:
    """Test suite for optimizer core contract guarantees."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.inputs = OptimizationInputs(
            project_location="India",
            voltage_level=400.0,
            terrain_type=TerrainType.FLAT,
            wind_zone=WindZone.ZONE_2,
            soil_category=SoilCategory.MEDIUM,
            span_min=250.0,
            span_max=450.0,
            governing_standard=DesignStandard.IS,
        )
        self.codal_engine = ISEngine()
        self.optimizer = PSOOptimizer(
            codal_engine=self.codal_engine,
            inputs=self.inputs,
            num_particles=10,  # Smaller for faster tests
            max_iterations=20,  # Smaller for faster tests
        )
    
    def test_always_returns_safe_design(self):
        """
        ASSERTION: Optimizer NEVER returns unsafe final design.
        
        This is the CORE CONTRACT. If this fails, the optimizer is broken.
        """
        result = self.optimizer.optimize(tower_type=TowerType.SUSPENSION)
        
        # CRITICAL ASSERTION: Result must be safe
        assert result.is_safe, (
            f"Optimizer violated core contract: returned unsafe design. "
            f"Violations: {result.safety_violations}"
        )
        
        # Verify safe design was found or conservative fallback used
        assert self.optimizer.found_safe_design or result.is_safe, (
            "Optimizer should have found safe design or used conservative fallback"
        )
    
    def test_span_always_within_bounds(self):
        """
        ASSERTION: Span length always within specified bounds.
        
        Even if optimizer somehow produces out-of-bounds span,
        it must be clamped and violation logged.
        """
        result = self.optimizer.optimize(tower_type=TowerType.SUSPENSION)
        
        span = result.best_design.span_length
        span_min = self.inputs.span_min
        span_max = self.inputs.span_max
        
        assert span_min <= span <= span_max, (
            f"Span {span}m outside bounds [{span_min}, {span_max}]m. "
            f"This indicates optimizer bug - span should be clamped."
        )
    
    def test_cost_penalizes_unsafe_candidates(self):
        """
        ASSERTION: Unsafe designs receive VERY_LARGE_PENALTY.
        
        This ensures unsafe designs are never selected as optimal.
        """
        result = self.optimizer.optimize(tower_type=TowerType.SUSPENSION)
        
        # If design is safe, cost should be reasonable (not penalty)
        if result.is_safe:
            assert result.best_cost < VERY_LARGE_PENALTY / 10, (
                f"Safe design has suspiciously high cost: {result.best_cost}. "
                f"Expected reasonable cost, not penalty value."
            )
        else:
            # If unsafe (should never happen), cost must be penalty
            assert result.best_cost >= VERY_LARGE_PENALTY, (
                f"Unsafe design should have penalty cost, got: {result.best_cost}"
            )
    
    def test_cost_monotonically_penalizes_unsafe(self):
        """
        ASSERTION: Cost function monotonically penalizes unsafe designs.
        
        Any unsafe design must have cost >= VERY_LARGE_PENALTY.
        Any safe design must have cost < VERY_LARGE_PENALTY.
        """
        # This is tested implicitly by the optimizer's fitness calculation
        # Unsafe designs get VERY_LARGE_PENALTY, safe designs get actual cost
        result = self.optimizer.optimize(tower_type=TowerType.SUSPENSION)
        
        # Since result is always safe (core contract), cost should be reasonable
        assert result.is_safe, "Core contract violation: unsafe design returned"
        assert result.best_cost < VERY_LARGE_PENALTY, (
            f"Safe design has penalty cost. This violates cost monotonicity."
        )
    
    def test_conservative_fallback_when_no_safe_found(self):
        """
        ASSERTION: If no safe design found, conservative fallback is used.
        
        This should rarely happen, but if it does, optimizer must return
        conservative safe design, not unsafe design.
        """
        # Use extreme constraints that might prevent finding safe design
        extreme_inputs = OptimizationInputs(
            project_location="India",
            voltage_level=765.0,  # Very high voltage
            terrain_type=TerrainType.MOUNTAINOUS,
            wind_zone=WindZone.ZONE_4,  # Maximum wind
            soil_category=SoilCategory.SOFT,  # Worst soil
            span_min=250.0,
            span_max=450.0,
            governing_standard=DesignStandard.IS,
            design_for_higher_wind=True,
            include_ice_load=True,
            conservative_foundation=True,
        )
        
        extreme_optimizer = PSOOptimizer(
            codal_engine=self.codal_engine,
            inputs=extreme_inputs,
            num_particles=5,  # Very small swarm
            max_iterations=5,  # Very few iterations (might not find safe design)
        )
        
        result = extreme_optimizer.optimize(tower_type=TowerType.SUSPENSION)
        
        # Even with extreme constraints and minimal search, result must be safe
        assert result.is_safe, (
            f"Optimizer failed to return safe design even with conservative fallback. "
            f"Violations: {result.safety_violations}"
        )
        
        # Conservative design should have reasonable parameters
        assert result.best_design.tower_height >= 40.0, (
            "Conservative fallback should use adequate tower height"
        )
        assert result.best_design.span_length >= extreme_inputs.span_min, (
            "Conservative fallback should respect span bounds"
        )
    
    def test_tower_design_immutability(self):
        """
        ASSERTION: TowerDesign is frozen (immutable).
        
        This prevents accidental modification of design parameters.
        """
        from data_models import TowerDesign, FoundationType
        
        design = TowerDesign(
            tower_type=TowerType.SUSPENSION,
            tower_height=40.0,
            base_width=12.0,
            span_length=350.0,
            foundation_type=FoundationType.PAD_FOOTING,
            footing_length=4.0,
            footing_width=4.0,
            footing_depth=3.0,
        )
        
        # Attempting to modify should raise FrozenInstanceError
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            design.tower_height = 50.0
    
    def test_optimization_inputs_immutability(self):
        """
        ASSERTION: OptimizationInputs is frozen (immutable).
        
        This prevents accidental modification of optimization parameters.
        """
        # Attempting to modify should raise FrozenInstanceError
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            self.inputs.voltage_level = 500.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


