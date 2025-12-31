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
from backend.services.location_deriver import (
    derive_location_from_coordinates,
    derive_wind_zone_from_location,
    classify_terrain_from_elevation_profile,
    reverse_geocode_simple,
)
from data_models import DesignStandard
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
    # Derive terrain from elevation profile if available, otherwise use manual input
    terrain_profile = input_dict.get('terrain_profile')
    terrain_input = input_dict.get('terrain')
    terrain_source = "user-selected"
    is_terrain_auto_detected = False
    
    if terrain_profile and len(terrain_profile) > 0:
        # Try to auto-classify terrain from elevation profile
        derived_terrain, is_auto = classify_terrain_from_elevation_profile(terrain_profile)
        if derived_terrain and is_auto:
            # Use auto-detected terrain if user didn't explicitly override
            if not terrain_input:
                terrain_input = derived_terrain
                terrain_source = "elevation-derived"
                is_terrain_auto_detected = True
            else:
                # User provided terrain, check if it matches auto-detected
                if terrain_input.lower() == derived_terrain.lower():
                    # User selection matches auto-detection
                    terrain_source = "elevation-derived"
                    is_terrain_auto_detected = True
                else:
                    # User overrode, keep their selection but mark it
                    terrain_source = "user-selected"
        else:
            # Auto-detection failed, use manual input
            if not terrain_input:
                raise ValueError("Terrain is required. Could not auto-detect from elevation profile.")
    else:
        # No terrain profile, require manual input
        if not terrain_input:
            raise ValueError("Terrain is required. Either provide terrain_profile or terrain.")
    
    # Parse terrain
    terrain_map = {
        'flat': TerrainType.FLAT,
        'rolling': TerrainType.ROLLING,
        'mountainous': TerrainType.MOUNTAINOUS,
        'desert': TerrainType.DESERT,
    }
    terrain_type = terrain_map.get(terrain_input.lower())
    if terrain_type is None:
        raise ValueError(f"Unknown terrain type: {terrain_input}")
    
    # Derive wind zone from location if route coordinates available, otherwise use manual input
    route_coordinates = input_dict.get('route_coordinates')  # Get route_coordinates for wind derivation
    wind_input = input_dict.get('wind')
    wind_source = "user-selected"
    is_wind_auto_detected = False
    
    if route_coordinates and len(route_coordinates) > 0:
        # Try to auto-derive wind zone from location
        first_coord = route_coordinates[0]
        lat = first_coord.get("lat")
        lon = first_coord.get("lon")
        
        if lat is not None and lon is not None:
            country_code = reverse_geocode_simple(lat, lon)
            if country_code:
                derived_wind, is_auto = derive_wind_zone_from_location(country_code, lat, lon)
                if derived_wind and is_auto:
                    # Use auto-detected wind if user didn't explicitly override
                    if not wind_input:
                        wind_input = derived_wind
                        wind_source = "map-derived"
                        is_wind_auto_detected = True
                    else:
                        # User provided wind, check if it matches auto-detected
                        if wind_input.lower() == derived_wind.lower():
                            # User selection matches auto-detection
                            wind_source = "map-derived"
                            is_wind_auto_detected = True
                        else:
                            # User overrode, keep their selection but mark it
                            wind_source = "user-selected"
                else:
                    # Auto-detection failed, use manual input
                    if not wind_input:
                        raise ValueError("Wind zone is required. Could not auto-detect from location.")
            else:
                # Country detection failed, use manual input
                if not wind_input:
                    raise ValueError("Wind zone is required. Could not determine country from coordinates.")
        else:
            # Coordinates missing, use manual input
            if not wind_input:
                raise ValueError("Wind zone is required. Route coordinates missing lat/lon.")
    else:
        # No route coordinates, require manual input
        if not wind_input:
            raise ValueError("Wind zone is required. Either provide route_coordinates or wind.")
    
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
    wind_zone = wind_map.get(wind_input.lower())
    if wind_zone is None:
        raise ValueError(f"Unknown wind zone: {wind_input}")
    
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
    
    # Derive location from route coordinates if available, otherwise use manual input
    route_coordinates = input_dict.get('route_coordinates')
    location = input_dict.get('location')
    is_location_auto_detected = False
    
    if route_coordinates and len(route_coordinates) > 0:
        # Auto-detect location from coordinates
        derived_location, derived_standard_str, is_auto = derive_location_from_coordinates(route_coordinates)
        if derived_location and derived_standard_str:
            location = derived_location
            is_location_auto_detected = is_auto
            # Convert standard string to enum
            standard_map = {
                "IS": DesignStandard.IS,
                "IEC": DesignStandard.IEC,
                "EUROCODE": DesignStandard.EUROCODE,
                "ASCE": DesignStandard.ASCE,
            }
            governing_standard = standard_map.get(derived_standard_str, DesignStandard.IS)
        else:
            # Fallback to manual location if auto-detection fails
            if not location:
                raise ValueError("Location is required. Could not auto-detect from coordinates.")
            governing_standard = get_governing_standard(location)
    else:
        # Use manual location input
        if not location:
            raise ValueError("Location is required. Either provide route_coordinates or location.")
        governing_standard = get_governing_standard(location)
    
    # Store auto-detection flags for confidence scoring
    input_dict['_location_auto_detected'] = is_location_auto_detected
    input_dict['_wind_auto_detected'] = is_wind_auto_detected
    input_dict['_terrain_auto_detected'] = is_terrain_auto_detected
    input_dict['_wind_source'] = wind_source
    input_dict['_terrain_source'] = terrain_source
    
    # Create optimization inputs
    inputs = OptimizationInputs(
        project_location=location,
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
        print(f"WARNING: Optimizer returned design with bounds violations: {bounds_violations}")
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
        terrain_profile=input_dict.get('terrain_profile'),
        location_auto_detected=input_dict.get('_location_auto_detected', False),
        wind_source=input_dict.get('_wind_source'),
        terrain_source=input_dict.get('_terrain_source'),
    )
    
    # Convert Pydantic model to dict for JSON serialization
    return canonical_result.dict()

