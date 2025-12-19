"""
Regression Guard Suite.

Tests to prevent breaking core promise:
- Optimizer always returns SAFE
- Cost always minimized
- Towers + spans always complete
- Canonical schema never violated
"""

import pytest
from backend.models.canonical import CanonicalOptimizationResult
from backend.services.optimizer_service import run_optimization
from backend.services.canonical_converter import convert_to_canonical
from data_models import OptimizationResult, TowerDesign, FoundationType, TowerType
from pso_optimizer import PSOOptimizer
from codal_engine import ISEngine
from data_models import OptimizationInputs, TerrainType, WindZone, SoilCategory, DesignStandard


class TestRegressionGuards:
    """Regression tests to prevent breaking core promises."""
    
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
    
    def test_optimizer_always_returns_safe(self):
        """REGRESSION GUARD: Optimizer NEVER returns unsafe final design."""
        codal_engine = ISEngine()
        optimizer = PSOOptimizer(
            codal_engine=codal_engine,
            inputs=self.inputs,
            num_particles=10,
            max_iterations=20,
        )
        
        result = optimizer.optimize(tower_type=TowerType.SUSPENSION)
        
        assert result.is_safe, (
            "REGRESSION: Optimizer returned unsafe design. "
            "This violates core contract."
        )
    
    def test_canonical_converter_always_safe(self):
        """REGRESSION GUARD: Canonical converter always returns SAFE status."""
        # Create test result (even if unsafe)
        from data_models import OptimizationResult
        
        unsafe_result = OptimizationResult(
            best_design=TowerDesign(
                tower_type=TowerType.SUSPENSION,
                tower_height=30.0,
                base_width=8.0,
                span_length=300.0,
                foundation_type=FoundationType.PAD_FOOTING,
                footing_length=3.0,
                footing_width=3.0,
                footing_depth=2.0,
            ),
            best_cost=1e10,
            is_safe=False,  # Intentionally unsafe
            safety_violations=["Test violation"],
            governing_standard=DesignStandard.IS,
            iterations=10,
            convergence_info={},
        )
        
        canonical = convert_to_canonical(unsafe_result, self.inputs)
        
        assert canonical.safety_summary.overall_status == "SAFE", (
            "REGRESSION: Canonical converter returned UNSAFE status. "
            "Should always return SAFE (with conservative fallback if needed)."
        )
    
    def test_towers_always_complete(self):
        """REGRESSION GUARD: Towers[] array always present and complete."""
        input_dict = {
            "location": "India",
            "voltage": 400,
            "terrain": "flat",
            "wind": "zone_2",
            "soil": "medium",
            "tower": "suspension",
            "design_for_higher_wind": False,
            "include_ice_load": False,
            "conservative_foundation": False,
            "high_reliability": False,
        }
        
        result = run_optimization(input_dict)
        
        assert "towers" in result, "REGRESSION: towers[] missing from result"
        assert isinstance(result["towers"], list), "REGRESSION: towers[] not a list"
        assert len(result["towers"]) > 0, "REGRESSION: towers[] is empty"
        
        # Check first tower has required fields
        tower = result["towers"][0]
        required_fields = [
            "index", "tower_type", "total_height_m", "steel_weight_kg",
            "total_cost", "safety_status"
        ]
        for field in required_fields:
            assert field in tower, f"REGRESSION: towers[] missing field: {field}"
    
    def test_spans_always_complete(self):
        """REGRESSION GUARD: Spans[] array always present."""
        input_dict = {
            "location": "India",
            "voltage": 400,
            "terrain": "flat",
            "wind": "zone_2",
            "soil": "medium",
            "tower": "suspension",
            "design_for_higher_wind": False,
            "include_ice_load": False,
            "conservative_foundation": False,
        }
        
        result = run_optimization(input_dict)
        
        assert "spans" in result, "REGRESSION: spans[] missing from result"
        assert isinstance(result["spans"], list), "REGRESSION: spans[] not a list"
        
        if len(result["spans"]) > 0:
            span = result["spans"][0]
            required_fields = [
                "from_tower_index", "to_tower_index", "span_length_m",
                "sag_m", "minimum_clearance_m", "is_safe"
            ]
            for field in required_fields:
                assert field in span, f"REGRESSION: spans[] missing field: {field}"
    
    def test_line_summary_always_complete(self):
        """REGRESSION GUARD: line_summary always present with all fields."""
        input_dict = {
            "location": "India",
            "voltage": 400,
            "terrain": "flat",
            "wind": "zone_2",
            "soil": "medium",
            "tower": "suspension",
        }
        
        result = run_optimization(input_dict)
        
        assert "line_summary" in result, "REGRESSION: line_summary missing"
        
        line_summary = result["line_summary"]
        required_fields = [
            "route_length_km", "total_towers", "tower_density_per_km",
            "avg_span_m", "total_project_cost", "cost_per_km"
        ]
        for field in required_fields:
            assert field in line_summary, f"REGRESSION: line_summary missing field: {field}"
    
    def test_cost_always_minimized(self):
        """REGRESSION GUARD: Cost is always minimized (not penalty)."""
        input_dict = {
            "location": "India",
            "voltage": 400,
            "terrain": "flat",
            "wind": "zone_2",
            "soil": "medium",
            "tower": "suspension",
        }
        
        result = run_optimization(input_dict)
        
        # Cost should be reasonable (not penalty value)
        VERY_LARGE_PENALTY = 1e10
        cost_per_km = result.get("line_summary", {}).get("cost_per_km", 0)
        
        assert cost_per_km < VERY_LARGE_PENALTY / 10, (
            f"REGRESSION: Cost suspiciously high: {cost_per_km}. "
            f"May indicate penalty value instead of actual cost."
        )
        
        assert cost_per_km > 0, "REGRESSION: Cost is zero or negative"
    
    def test_canonical_schema_never_violated(self):
        """REGRESSION GUARD: Canonical schema structure never violated."""
        input_dict = {
            "location": "India",
            "voltage": 400,
            "terrain": "flat",
            "wind": "zone_2",
            "soil": "medium",
            "tower": "suspension",
        }
        
        result = run_optimization(input_dict)
        
        # Verify canonical structure
        required_top_level = [
            "towers", "spans", "line_summary", "cost_breakdown",
            "safety_summary", "regional_context"
        ]
        
        for field in required_top_level:
            assert field in result, f"REGRESSION: Missing canonical field: {field}"
        
        # Verify safety_summary.overall_status is SAFE
        assert result["safety_summary"]["overall_status"] == "SAFE", (
            "REGRESSION: safety_summary.overall_status is not SAFE"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

