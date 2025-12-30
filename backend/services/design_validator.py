"""
Design Validation Service.

Validates tower positions and spans in real-time when towers are moved.
Also validates design bounds after optimization.
"""

import math
import logging
from typing import List, Dict, Any, Optional, Tuple
from auto_spotter import AutoSpotter, TerrainPoint, TowerPosition
from backend.services.obstacle_detector import ObstacleDetector
from backend.services.clearance_rules import ClearanceResolver
from backend.services.standard_resolver import resolve_standard
from backend.models.validation_request import SpanStatus
from data_models import OptimizationInputs, DesignStandard, TowerDesign

logger = logging.getLogger(__name__)


def validate_design_bounds(design: TowerDesign) -> List[str]:
    """
    Validate that a TowerDesign is within acceptable bounds.
    
    This is a defensive check to catch optimizer bugs that might produce
    invalid designs. Returns a list of violation messages, or empty list if valid.
    
    Args:
        design: TowerDesign to validate
        
    Returns:
        List of violation messages (empty if design is valid)
    """
    violations = []
    
    # Validate height bounds (typically 25-60m, but depends on voltage)
    if design.tower_height < 25.0:
        violations.append(f"Height {design.tower_height:.2f}m < minimum 25.0m")
    if design.tower_height > 60.0:
        violations.append(f"Height {design.tower_height:.2f}m > maximum 60.0m")
    
    # Validate base width (typically 25-40% of height)
    base_width_ratio = design.base_width / design.tower_height if design.tower_height > 0 else 0
    if base_width_ratio < 0.25:
        violations.append(f"Base width ratio {base_width_ratio:.2%} < minimum 25%")
    if base_width_ratio > 0.40:
        violations.append(f"Base width ratio {base_width_ratio:.2%} > maximum 40%")
    
    # Validate span bounds (typically 250-450m)
    if design.span_length < 250.0:
        violations.append(f"Span {design.span_length:.2f}m < minimum 250.0m")
    if design.span_length > 450.0:
        violations.append(f"Span {design.span_length:.2f}m > maximum 450.0m")
    
    # Validate footing dimensions
    if design.footing_length < 2.0:
        violations.append(f"Footing length {design.footing_length:.2f}m < minimum 2.0m")
    if design.footing_length > 10.0:
        violations.append(f"Footing length {design.footing_length:.2f}m > maximum 10.0m")
    
    if design.footing_width < 2.0:
        violations.append(f"Footing width {design.footing_width:.2f}m < minimum 2.0m")
    if design.footing_width > 10.0:
        violations.append(f"Footing width {design.footing_width:.2f}m > maximum 10.0m")
    
    if design.footing_depth < 1.0:
        violations.append(f"Footing depth {design.footing_depth:.2f}m < minimum 1.0m")
    if design.footing_depth > 5.0:
        violations.append(f"Footing depth {design.footing_depth:.2f}m > maximum 5.0m")
    
    return violations


def validate_design(
    towers: List[Dict[str, Any]],
    spans: List[Dict[str, Any]],
    voltage_kv: float,
    geo_context: Optional[Dict[str, Any]] = None,
    route_coordinates: Optional[List[Dict[str, Any]]] = None,
    terrain_profile: Optional[List[Dict[str, float]]] = None,
) -> Tuple[str, List[SpanStatus]]:
    """
    Validate design after tower movement.
    
    Args:
        towers: List of tower dicts with updated positions
        spans: List of span dicts connecting towers
        voltage_kv: Line voltage in kV
        geo_context: Geographic context for standard resolution
        route_coordinates: Route coordinates for obstacle detection
        terrain_profile: Terrain elevation profile
        
    Returns:
        Tuple of (overall_status, span_statuses)
    """
    span_statuses: List[SpanStatus] = []
    violations_count = 0
    
    # Convert terrain profile to TerrainPoint list
    terrain_points: List[TerrainPoint] = []
    if terrain_profile:
        for point in terrain_profile:
            terrain_points.append(TerrainPoint(
                distance_m=point.get('distance_m', point.get('x', 0.0)),
                elevation_m=point.get('elevation_m', point.get('z', 0.0)),
                latitude=None,
                longitude=None,
            ))
    
    # Get standard code from geo_context using standard resolver
    standard_code = 'IEC'  # Default fallback
    if geo_context and geo_context.get('country_code'):
        country_code = geo_context.get('country_code')
        # Use standard resolver to get standard code
        from backend.services.standard_resolver import StandardResolver
        resolver = StandardResolver()
        standard_info = resolver.resolve(country_code)
        # Extract the code from the standard info dict
        standard_code = standard_info.get('code', 'IEC')
        # Map to clearance rule code (IS -> IS, EN 50341 -> EN, etc.)
        if 'IS' in standard_code:
            standard_code = 'IS'
        elif 'EN' in standard_code or 'BS EN' in standard_code or 'NF EN' in standard_code or 'DIN EN' in standard_code or 'UNE EN' in standard_code:
            standard_code = 'EN'
        elif 'NESC' in standard_code:
            standard_code = 'NESC'
        else:
            standard_code = 'IEC'  # Fallback
    
    # Create clearance resolver
    resolver = ClearanceResolver(standard_code, voltage_kv)
    
    # Create obstacle detector if route coordinates available
    obstacles: List[Dict[str, Any]] = []
    if route_coordinates and terrain_points:
        try:
            detector = ObstacleDetector(
                route_coordinates=route_coordinates,
                terrain_profile=terrain_points,
            )
            obstacles = detector.get_obstacles_for_visualization()
        except Exception as e:
            logger.warning(f"Obstacle detection failed: {e}")
    
    # Validate each span
    for span_idx, span in enumerate(spans):
        from_idx = span.get('from_tower_index', 0)
        to_idx = span.get('to_tower_index', 0)
        
        # Find towers
        from_tower = next((t for t in towers if t.get('index') == from_idx), None)
        to_tower = next((t for t in towers if t.get('index') == to_idx), None)
        
        if not from_tower or not to_tower:
            span_statuses.append(SpanStatus(
                span_index=span_idx,
                from_tower_index=from_idx,
                to_tower_index=to_idx,
                status='VIOLATION',
                reason='Tower not found',
            ))
            violations_count += 1
            continue
        
        # Calculate span length (Haversine distance)
        from_lat = from_tower.get('latitude', 0)
        from_lon = from_tower.get('longitude', 0)
        to_lat = to_tower.get('latitude', 0)
        to_lon = to_tower.get('longitude', 0)
        
        span_length_m = _haversine_distance(from_lat, from_lon, to_lat, to_lon)
        
        # Get mid-point for obstacle checking
        mid_lat = (from_lat + to_lat) / 2.0
        mid_lon = (from_lon + to_lon) / 2.0
        
        # Calculate distance along route (approximate)
        mid_distance = span.get('span_length_m', span_length_m) / 2.0
        
        # Get required clearance (context-aware)
        required_clearance = resolver.get_required_clearance(mid_distance, obstacles)
        
        # Calculate actual clearance
        # Approximate: use average tower height minus sag
        from_height = from_tower.get('total_height_m', 40.0)
        to_height = to_tower.get('total_height_m', 40.0)
        avg_height = (from_height + to_height) / 2.0
        
        # Calculate sag (simplified)
        sag_m = _calculate_sag(span_length_m, voltage_kv)
        
        # Get ground elevation at mid-point
        mid_elevation = _interpolate_elevation(mid_distance, terrain_points)
        
        # Conductor height at mid-span (lowest point)
        from_elevation = from_tower.get('elevation_m', 0) if 'elevation_m' in from_tower else 0
        to_elevation = to_tower.get('elevation_m', 0) if 'elevation_m' in to_tower else 0
        avg_ground_elevation = (from_elevation + to_elevation) / 2.0
        
        conductor_height = avg_ground_elevation + avg_height - sag_m
        actual_clearance = conductor_height - mid_elevation
        
        # Check for violations
        if actual_clearance < required_clearance:
            violations_count += 1
            span_statuses.append(SpanStatus(
                span_index=span_idx,
                from_tower_index=from_idx,
                to_tower_index=to_idx,
                status='VIOLATION',
                reason=f'Clearance {actual_clearance:.1f}m < {required_clearance:.1f}m required',
                clearance_m=actual_clearance,
                required_clearance_m=required_clearance,
            ))
        else:
            span_statuses.append(SpanStatus(
                span_index=span_idx,
                from_tower_index=from_idx,
                to_tower_index=to_idx,
                status='SAFE',
                reason='Clearance requirements met',
                clearance_m=actual_clearance,
                required_clearance_m=required_clearance,
            ))
    
    overall_status = 'SAFE' if violations_count == 0 else 'VIOLATION'
    return overall_status, span_statuses


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula."""
    R = 6371000.0  # Earth radius in meters
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def _calculate_sag(span_length_m: float, voltage_kv: float) -> float:
    """Calculate approximate sag for clearance check."""
    # Simplified sag calculation
    if voltage_kv <= 132:
        if span_length_m <= 300:
            return 6.0
        elif span_length_m <= 400:
            return 7.0
        else:
            return 8.0
    elif voltage_kv <= 220:
        if span_length_m <= 300:
            return 7.0
        elif span_length_m <= 400:
            return 8.5
        else:
            return 10.0
    elif voltage_kv <= 400:
        if span_length_m <= 300:
            return 8.0
        elif span_length_m <= 400:
            return 9.5
        else:
            return 11.0
    else:
        # For > 400kV, use conservative estimate
        return span_length_m * 0.03  # 3% of span length


def _interpolate_elevation(distance_m: float, terrain_profile: List[TerrainPoint]) -> float:
    """Interpolate elevation at given distance."""
    if not terrain_profile or len(terrain_profile) < 2:
        return 0.0
    
    # Find surrounding points
    for i in range(len(terrain_profile) - 1):
        p1 = terrain_profile[i]
        p2 = terrain_profile[i + 1]
        
        if p1.distance_m <= distance_m <= p2.distance_m:
            # Linear interpolation
            if p2.distance_m == p1.distance_m:
                return p1.elevation_m
            
            ratio = (distance_m - p1.distance_m) / (p2.distance_m - p1.distance_m)
            return p1.elevation_m + ratio * (p2.elevation_m - p1.elevation_m)
    
    # Extrapolate if outside range
    if distance_m < terrain_profile[0].distance_m:
        return terrain_profile[0].elevation_m
    else:
        return terrain_profile[-1].elevation_m
