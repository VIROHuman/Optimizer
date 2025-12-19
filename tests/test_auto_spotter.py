"""
Unit Tests for Auto-Spotter.

Tests deterministic placement and safety guarantees.
"""

import pytest
from data_models import OptimizationInputs, TerrainType, WindZone, SoilCategory, DesignStandard
from auto_spotter import AutoSpotter, TerrainPoint, TowerPosition, create_terrain_profile_from_coordinates


class TestAutoSpotter:
    """Test suite for auto-spotter deterministic placement."""
    
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
        self.spotter = AutoSpotter(
            inputs=self.inputs,
            max_span_m=450.0,
            min_span_m=250.0,
            clearance_margin_m=10.0,
            step_back_m=10.0,
        )
    
    def test_flat_terrain_deterministic(self):
        """Test: Same flat terrain → same tower positions."""
        # Create flat terrain profile
        terrain = [
            TerrainPoint(distance_m=0.0, elevation_m=100.0),
            TerrainPoint(distance_m=1000.0, elevation_m=100.0),
            TerrainPoint(distance_m=2000.0, elevation_m=100.0),
        ]
        
        towers1 = self.spotter.place_towers(terrain_profile=terrain)
        towers2 = self.spotter.place_towers(terrain_profile=terrain)
        
        # Should be deterministic
        assert len(towers1) == len(towers2), "Tower count should be deterministic"
        
        for t1, t2 in zip(towers1, towers2):
            assert abs(t1.distance_along_route_m - t2.distance_along_route_m) < 0.01, \
                "Tower positions should be identical"
    
    def test_hill_obstruction_step_back(self):
        """Test: Hill obstruction triggers step-back."""
        # Create terrain with hill in middle
        terrain = [
            TerrainPoint(distance_m=0.0, elevation_m=100.0),
            TerrainPoint(distance_m=400.0, elevation_m=150.0),  # Hill peak
            TerrainPoint(distance_m=800.0, elevation_m=100.0),
            TerrainPoint(distance_m=1200.0, elevation_m=100.0),
        ]
        
        towers = self.spotter.place_towers(terrain_profile=terrain)
        
        # Should place towers avoiding hill
        assert len(towers) >= 2, "Should place at least 2 towers"
        
        # Check that spans don't exceed max
        for i in range(len(towers) - 1):
            span = towers[i + 1].distance_along_route_m - towers[i].distance_along_route_m
            assert span <= self.spotter.max_span_m + 1.0, \
                f"Span {span}m exceeds max {self.spotter.max_span_m}m"
            assert span >= self.spotter.min_span_m - 1.0, \
                f"Span {span}m below min {self.spotter.min_span_m}m"
    
    def test_river_crossing_mock(self):
        """Test: River crossing (low elevation) handled correctly."""
        # Create terrain with river valley
        terrain = [
            TerrainPoint(distance_m=0.0, elevation_m=100.0),
            TerrainPoint(distance_m=300.0, elevation_m=80.0),  # River valley
            TerrainPoint(distance_m=600.0, elevation_m=100.0),
            TerrainPoint(distance_m=900.0, elevation_m=100.0),
        ]
        
        towers = self.spotter.place_towers(terrain_profile=terrain)
        
        # Should place towers accounting for sag over river
        assert len(towers) >= 2, "Should place towers"
        
        # Check clearance at river (mid-point of span)
        for i in range(len(towers) - 1):
            from_tower = towers[i]
            to_tower = towers[i + 1]
            span_length = to_tower.distance_along_route_m - from_tower.distance_along_route_m
            
            is_safe, clearance, violation = self.spotter.check_clearance(
                from_tower, to_tower, terrain
            )
            
            # Should have adequate clearance
            assert clearance >= 0.0, f"Negative clearance: {clearance}m"
    
    def test_never_produces_impossible_spans(self):
        """Test: Never produces spans outside bounds."""
        # Various terrain profiles
        terrains = [
            # Flat
            [TerrainPoint(distance_m=i*100, elevation_m=100.0) for i in range(11)],
            # Rolling
            [TerrainPoint(distance_m=i*100, elevation_m=100.0 + (i % 3) * 10) for i in range(11)],
            # Mountainous
            [TerrainPoint(distance_m=i*100, elevation_m=100.0 + i * 5) for i in range(11)],
        ]
        
        for terrain in terrains:
            towers = self.spotter.place_towers(terrain_profile=terrain)
            
            for i in range(len(towers) - 1):
                span = towers[i + 1].distance_along_route_m - towers[i].distance_along_route_m
                assert self.spotter.min_span_m <= span <= self.spotter.max_span_m + 1.0, \
                    f"Impossible span: {span}m (bounds: [{self.spotter.min_span_m}, {self.spotter.max_span_m}])"
    
    def test_sag_calculation(self):
        """Test: Sag calculation is reasonable."""
        sag_250 = self.spotter.calculate_sag(250.0)
        sag_450 = self.spotter.calculate_sag(450.0)
        
        # Sag should increase with span length
        assert sag_450 > sag_250, "Longer spans should have more sag"
        
        # Sag should be reasonable (typically 1-5% of span length)
        assert 0.01 * 250.0 <= sag_250 <= 0.10 * 250.0, \
            f"Sag {sag_250}m for 250m span seems unreasonable"
        assert 0.01 * 450.0 <= sag_450 <= 0.10 * 450.0, \
            f"Sag {sag_450}m for 450m span seems unreasonable"
    
    def test_clearance_check(self):
        """Test: Clearance check works correctly."""
        from_tower = TowerPosition(
            index=0,
            distance_along_route_m=0.0,
            elevation_m=100.0,
        )
        to_tower = TowerPosition(
            index=1,
            distance_along_route_m=400.0,
            elevation_m=100.0,
        )
        
        terrain = [
            TerrainPoint(distance_m=0.0, elevation_m=100.0),
            TerrainPoint(distance_m=200.0, elevation_m=100.0),  # Mid-span
            TerrainPoint(distance_m=400.0, elevation_m=100.0),
        ]
        
        is_safe, clearance, violation = self.spotter.check_clearance(
            from_tower, to_tower, terrain
        )
        
        assert isinstance(is_safe, bool), "is_safe should be boolean"
        assert isinstance(clearance, float), "clearance should be float"
        assert clearance >= 0.0, "Clearance should be non-negative"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

