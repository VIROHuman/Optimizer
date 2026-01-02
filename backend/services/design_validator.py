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
            try:
                safe_msg = str(e).encode('ascii', errors='replace').decode('ascii')
                logger.warning(f"Obstacle detection failed: {safe_msg}")
            except Exception:
                logger.warning("Obstacle detection failed: [encoding error]")
    
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


def validate_and_adjust_tower(
    tower_dict: Dict[str, Any],
    span_length_m: float,
    voltage_kv: float,
    inputs: OptimizationInputs,
) -> Dict[str, Any]:
    """
    Validate and adjust tower for vertical clearance and slenderness ratio.
    
    This function:
    1. Checks vertical clearance (height vs sag)
    2. Checks slenderness ratio (base width vs height)
    3. Adjusts dimensions if needed
    4. Recalculates costs
    
    Args:
        tower_dict: Tower dictionary with design parameters
        span_length_m: Span length for sag calculation
        voltage_kv: Line voltage in kV
        inputs: OptimizationInputs for cost recalculation
        
    Returns:
        Updated tower_dict with adjustments and original values tracked
    """
    from data_models import TowerDesign, FoundationType
    from cost_engine import calculate_cost_with_breakdown
    from backend.services.canonical_converter import calculate_steel_weight_kg
    
    # Store original values
    original_height = tower_dict.get('total_height_m', 40.0)
    original_base_width = tower_dict.get('base_width_m', 8.0)
    original_steel_weight = tower_dict.get('steel_weight_kg', 5000.0)
    original_steel_cost = tower_dict.get('steel_cost', 7000.0)
    original_total_cost = tower_dict.get('total_cost', 13600.0)
    
    tower_dict['original_height_m'] = original_height
    tower_dict['original_base_width_m'] = original_base_width
    
    current_height = original_height
    current_base_width = original_base_width
    adjustments = []
    status = tower_dict.get('safety_status', 'SAFE')
    design_reason = tower_dict.get('design_reason', '') or ''
    
    # ========================================================================
    # 1. VERTICAL CLEARANCE VALIDATION
    # ========================================================================
    # Determine required ground clearance
    if voltage_kv < 132:
        ground_clearance = 6.0
        structural_spacing = 4.0
    elif voltage_kv < 400:
        ground_clearance = 7.0  # Standard 220kV
        structural_spacing = 6.0
    else:  # >= 400kV
        ground_clearance = 8.5
        structural_spacing = 9.0
    
    # Estimate sag (parabolic approximation: 3% of span for worst-case)
    estimated_sag = span_length_m * 0.03
    
    # Calculate minimum physics height
    min_physics_height = ground_clearance + estimated_sag + structural_spacing
    min_physics_height = math.ceil(min_physics_height)  # Round up
    
    # Check & adjust height
    if current_height < min_physics_height:
        old_height = current_height
        current_height = min_physics_height
        adjustments.append(f"Height increased from {old_height:.2f}m to {current_height:.2f}m for vertical clearance (sag: {estimated_sag:.2f}m)")
        
        if status == 'SAFE':
            status = 'GOVERNING'
        
        if design_reason:
            design_reason += " | Height increased for vertical clearance (sag)."
        else:
            design_reason = "Height increased for vertical clearance (sag)."
    
    # ========================================================================
    # 2. SLENDERNESS RATIO VALIDATION
    # ========================================================================
    MIN_ASPECT_RATIO = 1.0 / 6.0  # Base width must be at least 1/6th of height
    min_required_width = current_height * MIN_ASPECT_RATIO
    
    if current_base_width < min_required_width:
        old_width = current_base_width
        current_base_width = min_required_width
        adjustments.append(f"Base widened from {old_width:.2f}m to {current_base_width:.2f}m for structural stability (1:6 ratio)")
        
        if status == 'SAFE':
            status = 'GOVERNING'
        
        if design_reason:
            design_reason += " | Base widened for structural stability (1:6 ratio)"
        else:
            design_reason = "Base widened for structural stability (1:6 ratio)"
    
    # ========================================================================
    # 3. RECALCULATE COSTS IF ADJUSTMENTS WERE MADE
    # ========================================================================
    if adjustments:
        # Recalculate steel weight
        # Height change: square law (weight proportional to height^2)
        height_ratio = current_height / original_height if original_height > 0 else 1.0
        
        # Base width change: 40% weight increase for every 100% width increase
        width_ratio = current_base_width / original_base_width if original_base_width > 0 else 1.0
        width_weight_factor = 1.0 + (width_ratio - 1.0) * 0.4
        
        # Combined weight factor
        new_steel_weight = original_steel_weight * (height_ratio ** 2) * width_weight_factor
        
        # Recalculate cost using updated design
        try:
            from data_models import TowerType
            # Convert tower_type string to enum
            tower_type_str = tower_dict.get('tower_type', 'suspension')
            tower_type_enum = TowerType.SUSPENSION  # Default
            if tower_type_str == 'angle':
                tower_type_enum = TowerType.ANGLE
            elif tower_type_str == 'tension':
                tower_type_enum = TowerType.TENSION
            elif tower_type_str == 'dead_end':
                tower_type_enum = TowerType.DEAD_END
            
            updated_design = TowerDesign(
                tower_type=tower_type_enum,
                tower_height=current_height,
                base_width=current_base_width,
                span_length=span_length_m,
                foundation_type=FoundationType.PAD_FOOTING,
                footing_length=tower_dict.get('foundation_dimensions', {}).get('length', 4.0),
                footing_width=tower_dict.get('foundation_dimensions', {}).get('width', 4.0),
                footing_depth=tower_dict.get('foundation_dimensions', {}).get('depth', 3.0),
            )
            
            _, cost_breakdown = calculate_cost_with_breakdown(updated_design, inputs)
            
            # Update tower dict with new values
            tower_dict['total_height_m'] = current_height
            tower_dict['base_width_m'] = current_base_width
            tower_dict['steel_weight_kg'] = new_steel_weight
            tower_dict['steel_cost'] = cost_breakdown.get('steel_cost', original_steel_cost)
            # Update all cost components
            tower_dict['foundation_cost'] = cost_breakdown.get('foundation_cost', tower_dict.get('foundation_cost', 0))
            tower_dict['erection_cost'] = cost_breakdown.get('erection_cost', tower_dict.get('erection_cost', 0))
            tower_dict['transport_cost'] = cost_breakdown.get('transport_cost', tower_dict.get('transport_cost', 0))
            tower_dict['land_ROW_cost'] = cost_breakdown.get('land_cost', tower_dict.get('land_ROW_cost', 0))
            tower_dict['total_cost'] = cost_breakdown.get('total_cost', original_total_cost)
            tower_dict['safety_status'] = status
            tower_dict['design_reason'] = design_reason
            tower_dict['validation_adjustments'] = adjustments
            # Update base_height_m and body_extension_m proportionally
            if current_height != original_height:
                height_ratio = current_height / original_height if original_height > 0 else 1.0
                tower_dict['base_height_m'] = tower_dict.get('base_height_m', current_height * 0.4) * height_ratio
                tower_dict['body_extension_m'] = tower_dict.get('body_extension_m', current_height * 0.6) * height_ratio
            
        except Exception as e:
            # If cost recalculation fails, use approximate scaling
            try:
                safe_msg = str(e).encode('ascii', errors='replace').decode('ascii')
                logger.warning(f"Cost recalculation failed during validation: {safe_msg}")
            except Exception:
                logger.warning("Cost recalculation failed during validation: [encoding error]")
            
            # Approximate cost scaling
            cost_ratio = new_steel_weight / original_steel_weight if original_steel_weight > 0 else 1.0
            tower_dict['total_height_m'] = current_height
            tower_dict['base_width_m'] = current_base_width
            tower_dict['steel_weight_kg'] = new_steel_weight
            tower_dict['steel_cost'] = original_steel_cost * cost_ratio
            # Scale other costs proportionally (conservative estimate)
            tower_dict['total_cost'] = original_total_cost * cost_ratio
            tower_dict['safety_status'] = status
            tower_dict['design_reason'] = design_reason
            tower_dict['validation_adjustments'] = adjustments
            # Update base_height_m and body_extension_m proportionally
            if current_height != original_height:
                height_ratio = current_height / original_height if original_height > 0 else 1.0
                tower_dict['base_height_m'] = tower_dict.get('base_height_m', current_height * 0.4) * height_ratio
                tower_dict['body_extension_m'] = tower_dict.get('body_extension_m', current_height * 0.6) * height_ratio
    
    return tower_dict


def _calculate_wind_load(
    tower: Dict[str, Any],
    wind_pressure: float,
    span_length: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Calculate wind load using Gradient Wind + Conductor Load model.
    
    This function implements a robust, runtime-safe wind load calculation that:
    1. Handles missing span_length gracefully (defaults to 350m)
    2. Estimates face_area if not provided
    3. Applies gradient wind factors (k2) across 3 tower zones
    4. Calculates conductor load from wires
    5. Returns total moment and uplift force
    
    Args:
        tower: Tower dictionary with design parameters.
            Required keys: 'total_height_m' or 'height' (tower height in meters)
            Required keys: 'base_width_m' or 'base_width' (base width in meters)
            Optional keys: 'face_area' (if missing, will be estimated)
        wind_pressure: Wind pressure in kN/m² (typically 0.8-1.2 kN/m² for zones 1-4)
        span_length: Optional span length in meters (defaults to 350m if None)
        
    Returns:
        Tuple of (total_moment_knm, uplift_force_kn)
        Returns (0.0, 0.0) if critical data is missing (defensive coding)
    
    Example Usage:
        # Get wind pressure from wind zone (see foundation_safety_service.py for reference)
        wind_pressure_kpa = {
            "zone_1": 0.8,
            "zone_2": 1.0,
            "zone_3": 1.2,
            "zone_4": 1.5,
        }.get(inputs.wind_zone.value, 0.8)
        wind_pressure_kn_m2 = wind_pressure_kpa  # kPa = kN/m²
        
        # Calculate wind load
        total_moment, uplift_force = _calculate_wind_load(
            tower=tower_dict,
            wind_pressure=wind_pressure_kn_m2,
            span_length=span_length_m,  # Can be None, will default to 350m
        )
    """
    # ========================================================================
    # STEP B: SAFE MATH - Handle Missing Data
    # ========================================================================
    # Handle missing span_length
    safe_span = span_length if span_length is not None else 350.0
    
    # Get tower dimensions with safe defaults
    tower_height = tower.get('total_height_m', tower.get('height', 40.0))
    tower_base_width = tower.get('base_width_m', tower.get('base_width', 8.0))
    
    # Validate we have minimum required data
    if tower_height <= 0 or tower_base_width <= 0:
        try:
            safe_msg = f"Invalid tower dimensions: height={tower_height}, base_width={tower_base_width}".encode('ascii', errors='replace').decode('ascii')
            logger.warning(f"Wind load calculation skipped: {safe_msg}")
        except Exception:
            logger.warning("Wind load calculation skipped: Invalid tower dimensions")
        return (0.0, 0.0)
    
    # Estimate missing face_area
    face_area = tower.get('face_area', None)
    if face_area is None or face_area <= 0:
        # Estimate average width (assume top width is 1m)
        avg_width = (tower_base_width + 1.0) / 2.0
        # Assume 30% solidity ratio (typical for lattice towers)
        estimated_face_area = tower_height * avg_width * 0.3
        face_area = estimated_face_area
    else:
        face_area = float(face_area)
    
    # ========================================================================
    # STEP C: GRADIENT WIND LOGIC - Tower Body Load (3 Zones)
    # ========================================================================
    # Split face_area into 3 equal parts
    zone_area = face_area / 3.0
    
    # k2 factors for gradient wind (height-dependent wind speed increase)
    k2_bottom = 1.0   # Bottom zone: no gradient effect
    k2_mid = 1.15     # Mid zone: 15% increase
    k2_top = 1.30     # Top zone: 30% increase
    
    # Calculate forces for each zone
    force_bottom = (wind_pressure * k2_bottom) * zone_area
    force_mid = (wind_pressure * k2_mid) * zone_area
    force_top = (wind_pressure * k2_top) * zone_area
    
    # Calculate centroid heights for each zone (from base)
    zone_height = tower_height / 3.0
    centroid_bottom = zone_height / 2.0  # Center of bottom zone
    centroid_mid = zone_height + (zone_height / 2.0)  # Center of mid zone
    centroid_top = (2.0 * zone_height) + (zone_height / 2.0)  # Center of top zone
    
    # Calculate moments for each zone (Force × Centroid Height)
    moment_bottom = force_bottom * centroid_bottom
    moment_mid = force_mid * centroid_mid
    moment_top = force_top * centroid_top
    
    # Sum tower body moments
    moment_body = moment_bottom + moment_mid + moment_top
    
    # ========================================================================
    # STEP C: CONDUCTOR LOAD
    # ========================================================================
    # Wire area calculation:
    # - 30mm diameter conductor (typical for 220-400kV)
    # - 3 phases
    # - Area per phase = π × (diameter/2)² = π × (0.03/2)² ≈ 0.000707 m²
    # - Total wire area = 3 phases × 0.000707 m² ≈ 0.00212 m² per meter
    # - For span length: wire_area = safe_span × 0.00212
    # Simplified: wire_area = safe_span * 0.03 * 3 (approximate, using 30mm as factor)
    wire_area_per_meter = 0.00212  # m² per meter (3 phases, 30mm dia)
    wire_area = safe_span * wire_area_per_meter
    
    # Conductor wind force (apply k2_top factor for conductors at tower top)
    wire_force = (wind_pressure * 1.30) * wire_area
    
    # Moment from wires (assume wires at tower top height)
    moment_wires = wire_force * tower_height
    
    # ========================================================================
    # STEP D: FINAL OUTPUT
    # ========================================================================
    total_moment = moment_body + moment_wires
    
    # Uplift force = total moment / base width (simplified lever arm)
    uplift_force = total_moment / tower_base_width if tower_base_width > 0 else 0.0
    
    return (total_moment, uplift_force)
