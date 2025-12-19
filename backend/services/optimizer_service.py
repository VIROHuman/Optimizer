"""
Optimizer Service Module.

Extracts core optimization logic into a reusable service.
Used by both CLI (main.py) and API (api.py).
"""

from typing import Dict, Any, Optional
from data_models import (
    OptimizationInputs, DesignStandard, TowerType,
    TerrainType, WindZone, SoilCategory
)
from location_to_code import get_governing_standard
from codal_engine import (
    ISEngine, IECEngine, EurocodeEngine, ASCEEngine
)
from pso_optimizer import PSOOptimizer
from cost_engine import (
    calculate_cost_with_breakdown, 
    calculate_row_corridor_cost_per_km,
    check_cost_sanity
)
from constructability_engine import check_constructability
from regional_risk_registry import get_regional_risks
from dominant_risk_advisory import generate_risk_advisories
from intelligence.intelligence_manager import IntelligenceManager
from backend.services.design_validator import validate_design_bounds
from backend.services.canonical_converter import convert_to_canonical


def create_codal_engine(standard: DesignStandard):
    """
    Create appropriate codal engine instance.
    
    Args:
        standard: DesignStandard enum
        
    Returns:
        CodalEngine instance
    """
    engines = {
        DesignStandard.IS: ISEngine,
        DesignStandard.IEC: IECEngine,
        DesignStandard.EUROCODE: EurocodeEngine,
        DesignStandard.ASCE: ASCEEngine,
    }
    
    engine_class = engines.get(standard)
    if engine_class is None:
        raise ValueError(f"Unsupported design standard: {standard}")
    
    return engine_class()


def parse_input_dict(input_dict: Dict[str, Any]) -> tuple[OptimizationInputs, TowerType]:
    """
    Parse input dictionary into OptimizationInputs and TowerType.
    
    Args:
        input_dict: Dictionary with keys:
            - location: str
            - voltage: int
            - terrain: str
            - wind: str
            - soil: str
            - tower: str
            - design_for_higher_wind: bool
            - include_ice_load: bool
            - conservative_foundation: bool
            - high_reliability: bool (optional)
            - span_min: float (optional)
            - span_max: float (optional)
            - particles: int (optional)
            - iterations: int (optional)
    
    Returns:
        Tuple of (OptimizationInputs, TowerType)
    """
    # Parse terrain
    terrain_map = {
        'flat': TerrainType.FLAT,
        'rolling': TerrainType.ROLLING,
        'mountainous': TerrainType.MOUNTAINOUS,
        'desert': TerrainType.DESERT,
    }
    terrain_type = terrain_map.get(input_dict['terrain'].lower())
    if terrain_type is None:
        raise ValueError(f"Unknown terrain type: {input_dict['terrain']}")
    
    # Parse wind zone
    wind_map = {
        'zone_1': WindZone.ZONE_1,
        'zone_2': WindZone.ZONE_2,
        'zone_3': WindZone.ZONE_3,
        'zone_4': WindZone.ZONE_4,
        '1': WindZone.ZONE_1,
        '2': WindZone.ZONE_2,
        '3': WindZone.ZONE_3,
        '4': WindZone.ZONE_4,
    }
    wind_zone = wind_map.get(input_dict['wind'].lower())
    if wind_zone is None:
        raise ValueError(f"Unknown wind zone: {input_dict['wind']}")
    
    # Handle higher wind design scenario
    design_wind_zone = wind_zone
    if input_dict.get('design_for_higher_wind', False):
        wind_zone_map = {
            WindZone.ZONE_1: WindZone.ZONE_2,
            WindZone.ZONE_2: WindZone.ZONE_3,
            WindZone.ZONE_3: WindZone.ZONE_4,
            WindZone.ZONE_4: WindZone.ZONE_4,
        }
        design_wind_zone = wind_zone_map.get(wind_zone, wind_zone)
    
    # Parse soil
    soil_map = {
        'soft': SoilCategory.SOFT,
        'medium': SoilCategory.MEDIUM,
        'hard': SoilCategory.HARD,
        'rock': SoilCategory.ROCK,
    }
    soil_category = soil_map.get(input_dict['soil'].lower())
    if soil_category is None:
        raise ValueError(f"Unknown soil category: {input_dict['soil']}")
    
    # Parse tower type
    tower_map = {
        'suspension': TowerType.SUSPENSION,
        'tension': TowerType.TENSION,
        'dead_end': TowerType.TENSION,  # Alias
    }
    tower_type = tower_map.get(input_dict['tower'].lower())
    if tower_type is None:
        raise ValueError(f"Unknown tower type: {input_dict['tower']}")
    
    # Resolve governing standard
    governing_standard = get_governing_standard(input_dict['location'])
    
    # Create optimization inputs
    inputs = OptimizationInputs(
        project_location=input_dict['location'],
        voltage_level=input_dict['voltage'],
        terrain_type=terrain_type,
        wind_zone=design_wind_zone,
        soil_category=soil_category,
        span_min=input_dict.get('span_min', 250.0),  # Match original optimizer default
        span_max=input_dict.get('span_max', 450.0),  # Match original optimizer default
        governing_standard=governing_standard,
        design_for_higher_wind=input_dict.get('design_for_higher_wind', False),
        include_ice_load=input_dict.get('include_ice_load', False),
        high_reliability=input_dict.get('high_reliability', False),
        conservative_foundation=input_dict.get('conservative_foundation', False),
    )
    
    return inputs, tower_type


def run_optimization(input_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run optimization and return structured results.
    
    Args:
        input_dict: Input parameters dictionary
        
    Returns:
        Dictionary with all optimization results
    """
    # TASK 5.3 & 5.4: Check if route optimization should be used
    route_coordinates = input_dict.get('route_coordinates')
    terrain_profile = input_dict.get('terrain_profile')
    project_length_km = input_dict.get('project_length_km')
    
    # If route data is provided, use route optimization (TASK 5.4)
    if route_coordinates and len(route_coordinates) >= 2:
        from backend.services.route_optimizer import optimize_route
        
        # Convert terrain_profile format if provided
        # Frontend sends: [{ "x": distance_m, "z": elevation_m }]
        # Backend expects: route_coordinates with elevation_m and distance_m
        if terrain_profile:
            # Merge terrain profile into route coordinates
            for i, coord in enumerate(route_coordinates):
                # Find matching terrain point (closest by distance)
                if terrain_profile:
                    # Simple interpolation: find closest terrain point
                    min_dist = float('inf')
                    closest_elevation = 0.0
                    for tp in terrain_profile:
                        # Calculate distance from route point to terrain point
                        # For now, assume terrain points align with route points
                        if i < len(terrain_profile):
                            closest_elevation = terrain_profile[i].get('z', 0.0)
                            break
                    coord['elevation_m'] = closest_elevation
                    if 'distance_m' not in coord:
                        coord['distance_m'] = terrain_profile[i].get('x', 0.0) if i < len(terrain_profile) else 0.0
        
        # Calculate project length from route if not provided
        if not project_length_km:
            # Calculate from route coordinates using Haversine
            from math import radians, sin, cos, sqrt, atan2
            total_distance = 0.0
            for i in range(len(route_coordinates) - 1):
                lat1, lon1 = route_coordinates[i].get('lat', 0), route_coordinates[i].get('lon', 0)
                lat2, lon2 = route_coordinates[i+1].get('lat', 0), route_coordinates[i+1].get('lon', 0)
                R = 6371  # Earth radius in km
                dlat = radians(lat2 - lat1)
                dlon = radians(lon2 - lon1)
                a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                total_distance += R * c
            project_length_km = total_distance
        
        # Use route optimization
        design_options = {
            "location": input_dict.get('location'),
            "voltage": input_dict.get('voltage'),
            "terrain": input_dict.get('terrain'),
            "wind": input_dict.get('wind'),
            "soil": input_dict.get('soil'),
            "tower": input_dict.get('tower'),
            "design_for_higher_wind": input_dict.get('design_for_higher_wind', False),
            "include_ice_load": input_dict.get('include_ice_load', False),
            "conservative_foundation": input_dict.get('conservative_foundation', False),
            "high_reliability": input_dict.get('high_reliability', False),
        }
        
        result = optimize_route(
            route_coordinates=route_coordinates,
            project_length_km=project_length_km,
            design_options=design_options,
            row_mode=input_dict.get('row_mode', 'urban_private'),
            terrain_profile=terrain_profile,  # TASK 5.3: Pass terrain profile
        )
        
        return result.dict()
    
    # Otherwise, use single-tower optimization (existing logic)
    # Parse inputs
    inputs, tower_type = parse_input_dict(input_dict)
    
    # Create codal engine
    codal_engine = create_codal_engine(inputs.governing_standard)
    
    # Create optimizer
    optimizer = PSOOptimizer(
        codal_engine=codal_engine,
        inputs=inputs,
        num_particles=input_dict.get('particles', 30),
        max_iterations=input_dict.get('iterations', 100),
    )
    
    # Run optimization
    # Wrap in try-catch to ensure we always return structured response, never crash
    try:
        result = optimizer.optimize(tower_type=tower_type)
    except Exception as e:
        # If optimization fails, return error as violation, not exception
        # This ensures API contract is maintained
        import traceback
        error_msg = f"Optimization failed: {str(e)}"
        print(f"ERROR in optimization: {error_msg}")
        print(traceback.format_exc())
        
        # Return unsafe result with violation
        from data_models import OptimizationResult, TowerDesign, TowerType, FoundationType
        from datetime import datetime
        
        # Create a minimal invalid design to return
        dummy_design = TowerDesign(
            tower_type=tower_type,
            tower_height=40.0,
            base_width=10.0,
            span_length=350.0,
            foundation_type=FoundationType.PAD_FOOTING,
            footing_length=4.0,
            footing_width=4.0,
            footing_depth=3.0,
        )
        
        result = OptimizationResult(
            best_design=dummy_design,
            best_cost=float('inf'),
            is_safe=False,
            safety_violations=[error_msg],
            governing_standard=inputs.governing_standard,
            iterations=0,
            convergence_info={},
        )
    
    # Defensive check: Ensure returned design is within bounds
    # This catches any optimizer bugs that might produce invalid designs
    bounds_violations = validate_design_bounds(result.best_design)
    if bounds_violations:
        # Log the violation (indicates optimizer bug)
        print(f"WARNING: Optimizer returned design with bounds violations:")
        for violation in bounds_violations:
            print(f"  - {violation}")
        
        # Add bounds violations to safety violations
        if result.is_safe:
            # If design was marked safe but violates bounds, mark as unsafe
            result.is_safe = False
            result.safety_violations = bounds_violations
        else:
            # If already unsafe, append bounds violations
            result.safety_violations.extend(bounds_violations)
    
    # Convert to canonical format
    # Get project length if provided (for line-level estimates)
    project_length_km = input_dict.get('project_length_km')
    
    # Get route coordinates if provided (for map-based placement)
    route_coordinates = input_dict.get('route_coordinates')
    
    # Convert to canonical OptimizationResult
    canonical_result = convert_to_canonical(
        result=result,
        inputs=inputs,
        project_length_km=project_length_km,
        route_coordinates=route_coordinates,
        row_mode=input_dict.get('row_mode', 'urban_private'),
    )
    
    # Convert Pydantic model to dict for JSON serialization
    return canonical_result.dict()

