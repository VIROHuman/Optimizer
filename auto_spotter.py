"""
Auto Tower Spotter Module.

Automatically places towers along a drawn route based on terrain profile.
Eliminates hit-and-trial tower placement.

CRITICAL PRINCIPLE:
- Auto-spotter only decides WHERE towers go
- Optimizer decides HOW towers are designed
- No cost data in auto-spotter (cost comes from optimizer)

Algorithm:
1. Receive terrain profile (distance + elevation[])
2. Start at route start (Tower 1)
3. Attempt max allowed span
4. Check sag vs terrain clearance
5. If collision:
   - Step back 10m and retry
6. Place tower when safe
7. Repeat until route ends
"""

from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from data_models import OptimizationInputs


@dataclass
class TerrainPoint:
    """Single point along terrain profile."""
    distance_m: float  # Distance from route start
    elevation_m: float  # Ground elevation
    latitude: Optional[float] = None  # Optional GPS coordinates
    longitude: Optional[float] = None


@dataclass
class TowerPosition:
    """Tower position along route."""
    index: int  # Tower index (0-based)
    distance_along_route_m: float  # Distance from route start
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation_m: float = 0.0  # Ground elevation at tower location
    design_type: Optional[str] = None  # 'anchor' or 'suspension' (set by section-based placer)
    nudge_description: Optional[str] = None  # Description of any nudge applied (e.g., 'Shifted 12m fwd to avoid Highway')
    original_distance_m: Optional[float] = None  # Original proposed distance before nudge


class AutoSpotter:
    """
    Automatic tower placement along route.
    
    This module places towers based on:
    - Maximum allowed span length
    - Terrain clearance requirements
    - Conductor sag calculations
    
    It does NOT:
    - Optimize tower design (that's optimizer's job)
    - Calculate costs (that's cost engine's job)
    - Validate safety (that's codal engine's job)
    """
    
    # CRITICAL: Minimum span length (hard constraint for physical spacing)
    MIN_SPAN = 30.0  # meters - absolute minimum between any two towers
    
    def __init__(
        self,
        inputs: OptimizationInputs,
        max_span_m: float = 450.0,
        min_span_m: float = 250.0,
        clearance_margin_m: float = 10.0,  # Minimum clearance above ground
        step_back_m: float = 10.0,  # Step back distance when collision detected
    ):
        """
        Initialize auto spotter.
        
        Args:
            inputs: OptimizationInputs with project context
            max_span_m: Maximum allowed span length
            min_span_m: Minimum allowed span length
            clearance_margin_m: Minimum clearance above ground (m)
            step_back_m: Step back distance when collision detected (m)
        """
        self.inputs = inputs
        self.max_span_m = max_span_m
        # Ensure min_span_m is at least MIN_SPAN (hard constraint)
        self.min_span_m = max(min_span_m, self.MIN_SPAN)
        self.clearance_margin_m = clearance_margin_m
        self.step_back_m = step_back_m
    
    def calculate_sag(
        self,
        span_length_m: float,
        conductor_weight_per_m: float = 1.5,  # kg/m (typical ACSR)
        tension_kN: Optional[float] = None,  # If None, estimate from voltage and span
    ) -> float:
        """
        Calculate conductor sag at mid-span.
        
        Uses catenary approximation:
        sag ~= (weight * span^2) / (8 * tension)
        
        Args:
            span_length_m: Span length in meters
            conductor_weight_per_m: Conductor weight per meter (kg/m)
            tension_kN: Conductor tension (kN). If None, estimates from voltage and span.
            
        Returns:
            Sag at mid-span in meters
        """
        # Estimate tension if not provided
        if tension_kN is None:
            if hasattr(self, 'inputs') and self.inputs:
                voltage_kv = self.inputs.voltage_level
                # Estimate tension based on voltage and span length
                # Typical values: 400kV ~50-80 kN, 765kV ~80-120 kN per conductor
                base_tension = 30.0  # kN base tension
                voltage_factor = voltage_kv / 400.0  # Normalize to 400kV
                span_factor = span_length_m / 300.0  # Normalize to 300m span
                tension_kN = base_tension * voltage_factor * span_factor
                tension_kN = min(tension_kN, 150.0)  # Cap at 150 kN
            else:
                # Fallback to default if inputs not available
                tension_kN = 50.0
        
        # Convert weight to force (N/m)
        weight_per_m_N = conductor_weight_per_m * 9.81  # kg/m to N/m
        
        # Convert tension to N
        tension_N = tension_kN * 1000.0
        
        # Prevent division by zero
        if tension_N <= 0:
            tension_N = 1000.0  # Minimum 1 kN to prevent infinite sag
        
        # Catenary sag approximation
        sag_m = (weight_per_m_N * span_length_m * span_length_m) / (8.0 * tension_N)
        
        return sag_m
    
    def check_clearance(
        self,
        from_tower: TowerPosition,
        to_tower: TowerPosition,
        terrain_profile: List[TerrainPoint],
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Check if span has adequate clearance above terrain.
        
        Args:
            from_tower: Tower at span start
            to_tower: Tower at span end
            terrain_profile: Terrain elevation profile
            
        Returns:
            Tuple of (is_safe, minimum_clearance_m, violation_message)
        """
        span_length = to_tower.distance_along_route_m - from_tower.distance_along_route_m
        
        # Calculate sag
        sag_m = self.calculate_sag(span_length)
        
        # Get tower heights (will be optimized later, use conservative estimate)
        # For clearance check, assume towers are tall enough
        from_height = 40.0  # Conservative estimate
        to_height = 40.0
        
        # Mid-span point
        mid_distance = (from_tower.distance_along_route_m + to_tower.distance_along_route_m) / 2.0
        
        # Find terrain elevation at mid-span
        mid_elevation = self.interpolate_elevation(mid_distance, terrain_profile)
        
        # Conductor height at mid-span (lowest point due to sag)
        # Use average tower height minus sag
        avg_tower_top = (from_tower.elevation_m + from_height + to_tower.elevation_m + to_height) / 2.0
        conductor_height = avg_tower_top - sag_m
        
        # Clearance = conductor height - ground elevation
        clearance = conductor_height - mid_elevation
        
        # Check if clearance is adequate
        is_safe = clearance >= self.clearance_margin_m
        
        violation = None
        if not is_safe:
            violation = f"Insufficient clearance: {clearance:.2f}m < {self.clearance_margin_m}m required"
        
        return is_safe, clearance, violation
    
    def interpolate_elevation(self, distance_m: float, terrain_profile: List[TerrainPoint]) -> float:
        """
        Interpolate elevation at given distance.
        
        Args:
            distance_m: Distance from route start
            terrain_profile: Terrain elevation profile
            
        Returns:
            Interpolated elevation
        """
        if not terrain_profile:
            return 0.0
        
        # Find surrounding points
        for i in range(len(terrain_profile) - 1):
            p1 = terrain_profile[i]
            p2 = terrain_profile[i + 1]
            
            if p1.distance_m <= distance_m <= p2.distance_m:
                # Linear interpolation
                t = (distance_m - p1.distance_m) / (p2.distance_m - p1.distance_m)
                elevation = p1.elevation_m + t * (p2.elevation_m - p1.elevation_m)
                return elevation
        
        # Extrapolate if beyond profile
        if distance_m < terrain_profile[0].distance_m:
            return terrain_profile[0].elevation_m
        else:
            return terrain_profile[-1].elevation_m
    
    def place_towers(
        self,
        terrain_profile: List[TerrainPoint],
        route_start_lat: Optional[float] = None,
        route_start_lon: Optional[float] = None,
        route_coordinates: Optional[List[Dict[str, Any]]] = None,
    ) -> List[TowerPosition]:
        """
        Place towers along route based on terrain profile.
        
        Algorithm:
        1. Start at route start (Tower 0)
        2. Attempt max allowed span
        3. Check sag vs terrain clearance
        4. If collision: step back 10m and retry
        5. Place tower when safe
        6. Repeat until route ends
        
        Args:
            terrain_profile: Terrain elevation profile
            route_start_lat: Optional starting latitude
            route_start_lon: Optional starting longitude
            
        Returns:
            List of TowerPosition objects
        """
        if not terrain_profile:
            return []
        
        towers: List[TowerPosition] = []
        
        # Start at route beginning
        current_distance = 0.0
        tower_index = 0
        
        # Get route end distance (along actual polyline if route_coordinates exist)
        # CRITICAL: Use the LARGEST available distance to ensure we don't cut off the route
        route_end_distance = 0.0
        
        if route_coordinates and len(route_coordinates) > 0:
            # Get actual polyline distance from route_coordinates
            route_end_from_coords = route_coordinates[-1].get('distance_m', 0.0)
            if route_end_from_coords == 0.0:
                # Calculate cumulative distance if not provided
                route_end_from_coords = self._calculate_polyline_total_distance(route_coordinates)
            route_end_distance = route_end_from_coords
        
        # Also check terrain profile distance
        terrain_end_distance = terrain_profile[-1].distance_m if terrain_profile else 0.0
        
        # Use the MAXIMUM of both to ensure we don't miss any part of the route
        route_end_distance = max(route_end_distance, terrain_end_distance)
        
        # Log for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Auto-spotter: route_end_distance={route_end_distance:.2f}m, "
            f"terrain_profile_end={terrain_end_distance:.2f}m, "
            f"route_coordinates_count={len(route_coordinates) if route_coordinates else 0}"
        )
        
        if route_end_distance <= 0.0:
            logger.warning("Route end distance is 0 or negative! Cannot place towers.")
            return []
        
        logger.info(f"Starting tower placement: current_distance={current_distance:.2f}m, route_end={route_end_distance:.2f}m, max_span={self.max_span_m:.2f}m")
        
        while current_distance < route_end_distance:
            # CRITICAL: Enforce MIN_SPAN constraint
            # Ensure current tower is at least MIN_SPAN away from previous tower
            if len(towers) > 0:
                last_tower_distance = towers[-1].distance_along_route_m
                if current_distance - last_tower_distance < self.MIN_SPAN:
                    # Force placement at MIN_SPAN from last tower
                    current_distance = last_tower_distance + self.MIN_SPAN
                    # If this exceeds route end, we're done
                    if current_distance >= route_end_distance:
                        logger.info(f"Stopping: current_distance {current_distance:.2f}m >= route_end {route_end_distance:.2f}m")
                        break
            
            # Place tower at current position
            current_elevation = self.interpolate_elevation(current_distance, terrain_profile)
            
            # Get coordinates if available (using polyline walker for zigzag routes)
            lat, lon = self._get_coordinates_at_distance(
                current_distance, terrain_profile, route_start_lat, route_start_lon, route_coordinates
            )
            
            # Log coordinate retrieval for debugging
            if lat is None or lon is None:
                logger.warning(f"Tower {tower_index} at {current_distance:.2f}m: No coordinates retrieved (lat={lat}, lon={lon})")
            else:
                logger.info(f"Tower {tower_index} at {current_distance:.2f}m: coordinates=({lat:.6f}, {lon:.6f})")
            
            tower = TowerPosition(
                index=tower_index,
                distance_along_route_m=current_distance,
                latitude=lat,
                longitude=lon,
                elevation_m=current_elevation,
            )
            towers.append(tower)
            logger.info(f"Placed tower {tower_index} at distance {current_distance:.2f}m (lat={lat}, lon={lon})")
            
            # Try to place next tower at max span (along actual polyline)
            next_distance = current_distance + self.max_span_m
            logger.info(f"Attempting next tower at distance {next_distance:.2f}m (route_end={route_end_distance:.2f}m)")
            
            # If beyond route end, check if we need final tower
            if next_distance >= route_end_distance:
                # Check if remaining distance is sufficient for a new tower
                remaining_distance = route_end_distance - current_distance
                
                # CRITICAL: Only place final tower if there's meaningful distance remaining
                # Check if the last tower we placed is NOT already at the route end
                last_tower_at_end = len(towers) > 0 and towers[-1].distance_along_route_m >= route_end_distance - 0.1
                
                if remaining_distance >= self.MIN_SPAN and not last_tower_at_end:
                    # Place final tower at route end (only if we haven't placed it yet)
                    final_elevation = self.interpolate_elevation(route_end_distance, terrain_profile)
                    final_lat, final_lon = self._get_coordinates_at_distance(
                        route_end_distance, terrain_profile, route_start_lat, route_start_lon, route_coordinates
                    )
                    final_tower = TowerPosition(
                        index=tower_index + 1,
                        distance_along_route_m=route_end_distance,
                        latitude=final_lat,
                        longitude=final_lon,
                        elevation_m=final_elevation,
                    )
                    towers.append(final_tower)
                    logger.info(f"Placed final tower at route end: {route_end_distance:.2f}m")
                # Otherwise, extend previous span (don't place new tower)
                break
            
            # Check clearance for this span
            next_elevation = self.interpolate_elevation(next_distance, terrain_profile)
            next_lat, next_lon = self._get_coordinates_at_distance(
                next_distance, terrain_profile, route_start_lat, route_start_lon, route_coordinates
            )
            next_tower = TowerPosition(
                index=tower_index + 1,
                distance_along_route_m=next_distance,
                latitude=next_lat,
                longitude=next_lon,
                elevation_m=next_elevation,
            )
            
            is_safe, clearance, violation = self.check_clearance(tower, next_tower, terrain_profile)
            
            if is_safe:
                # Safe span, move to next tower
                # CRITICAL: Ensure MIN_SPAN constraint
                if next_distance - current_distance < self.MIN_SPAN:
                    # Force minimum span
                    next_distance = current_distance + self.MIN_SPAN
                    if next_distance >= route_end_distance:
                        break
                
                current_distance = next_distance
                tower_index += 1
            else:
                # Collision detected, step back
                current_distance = next_distance - self.step_back_m
                
                # CRITICAL: Ensure we don't go below MIN_SPAN
                if current_distance - tower.distance_along_route_m < self.MIN_SPAN:
                    # Can't step back further, place tower at MIN_SPAN
                    current_distance = tower.distance_along_route_m + self.MIN_SPAN
                    if current_distance >= route_end_distance:
                        # Can't place tower, extend previous span instead
                        break
                    tower_index += 1
                else:
                    # Continue trying
                    continue
        
        # CRITICAL: Validate tower sequencing (strict monotonic ordering)
        self._validate_tower_sequencing(towers)
        
        return towers
    
    def _calculate_polyline_total_distance(self, route_coordinates: List[Dict[str, Any]]) -> float:
        """
        Calculate total distance along polyline route.
        
        CRITICAL: Always calculates from lat/lon using Haversine formula.
        IGNORES distance_m attribute completely (it may be corrupted/incorrect).
        
        Args:
            route_coordinates: List of route points with lat/lon
            
        Returns:
            Total distance in meters along the polyline (calculated from coordinates)
        """
        import math
        
        if not route_coordinates or len(route_coordinates) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(len(route_coordinates) - 1):
            p1 = route_coordinates[i]
            p2 = route_coordinates[i + 1]
            
            lat1 = p1.get('lat')
            lon1 = p1.get('lon')
            lat2 = p2.get('lat')
            lon2 = p2.get('lon')
            
            if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
                continue
            
            # Calculate segment length using Haversine formula
            # This gives the actual physical distance between coordinates
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            segment_length = 6371000.0 * c  # Earth radius in meters
            total_distance += segment_length
        
        return total_distance
    
    def _validate_tower_sequencing(self, towers: List[TowerPosition]) -> None:
        """
        Validate that towers are in strict monotonic order with minimum span.
        
        Raises ValueError if validation fails.
        """
        if len(towers) < 2:
            return
        
        for i in range(len(towers) - 1):
            current = towers[i]
            next_tower = towers[i + 1]
            
            span = next_tower.distance_along_route_m - current.distance_along_route_m
            
            if span <= 0:
                raise ValueError(
                    f"Tower sequencing violation: Tower {i} at {current.distance_along_route_m:.2f}m "
                    f"must be before Tower {i+1} at {next_tower.distance_along_route_m:.2f}m"
                )
            
            if span < self.MIN_SPAN:
                raise ValueError(
                    f"Minimum span violation: Span between Tower {i} and {i+1} is {span:.2f}m, "
                    f"which is less than MIN_SPAN {self.MIN_SPAN:.2f}m"
                )
    
    def _get_coordinates_at_distance(
        self,
        distance_m: float,
        terrain_profile: List[TerrainPoint],
        route_start_lat: Optional[float],
        route_start_lon: Optional[float],
        route_coordinates: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Get coordinates at given distance along route using polyline walker.
        
        CRITICAL: This follows the actual zigzag route path, not a straight line.
        Uses polyline walker algorithm to ensure coordinates land on the actual route segments.
        
        Args:
            distance_m: Distance from route start (along actual route path)
            terrain_profile: Terrain profile (may contain lat/lon)
            route_start_lat: Starting latitude (fallback)
            route_start_lon: Starting longitude (fallback)
            route_coordinates: List of route points with lat/lon/distance_m (preferred)
            
        Returns:
            Tuple of (latitude, longitude) or (None, None) if not available
        """
        # CRITICAL FIX: Use polyline walker on route_coordinates if available
        # This ensures coordinates follow the actual zigzag path, not a straight line
        if route_coordinates and len(route_coordinates) >= 2:
            # Polyline walker will calculate distances from coordinates
            pass
            
            lat, lon = _polyline_walker_get_coordinates(route_coordinates, distance_m)
            import logging
            logger = logging.getLogger(__name__)
            if lat is not None and lon is not None:
                logger.info(f"Polyline walker: distance={distance_m:.2f}m -> ({lat:.6f}, {lon:.6f})")
                return lat, lon
            else:
                logger.warning(f"Polyline walker returned None for distance={distance_m:.2f}m")
                # DO NOT fall back - this is a critical error that must be fixed
                return None, None
        
        # Fallback: If terrain profile has coordinates, interpolate
        # This is more accurate when route_coordinates are sparse waypoints
        for i in range(len(terrain_profile) - 1):
            p1 = terrain_profile[i]
            p2 = terrain_profile[i + 1]
            
            if p1.distance_m <= distance_m <= p2.distance_m:
                if p1.latitude is not None and p1.longitude is not None and \
                   p2.latitude is not None and p2.longitude is not None:
                    # Linear interpolation
                    t = (distance_m - p1.distance_m) / (p2.distance_m - p1.distance_m)
                    lat = p1.latitude + t * (p2.latitude - p1.latitude)
                    lon = p1.longitude + t * (p2.longitude - p1.longitude)
                    logger.info(f"Terrain profile interpolation: distance={distance_m:.2f}m -> ({lat:.6f}, {lon:.6f})")
                    return lat, lon
        
        # If no coordinates available, return None
        logger.warning(f"No coordinates available for distance={distance_m:.2f}m")
        return None, None


def _polyline_walker_get_coordinates(
    route_coordinates: List[Dict[str, Any]],
    target_distance_m: float,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Polyline Walker Algorithm: Get coordinates at target distance along zigzag route.
    
    This function walks along the actual route segments (polyline), accumulating distance,
    and interpolates coordinates only when the target distance falls within a segment.
    
    This ensures that if a tower is placed at 500m on a zigzag route, the coordinates
    will land on the actual zigzag path, not on a straight line shortcut.
    
    Args:
        route_coordinates: List of route points, each with:
            - 'lat': latitude
            - 'lon': longitude
            - 'distance_m': cumulative distance from start (optional, will be calculated if missing)
        target_distance_m: Target distance along route (meters)
        
    Returns:
        Tuple of (latitude, longitude) or (None, None) if route is empty or invalid
    """
    import math
    
    if not route_coordinates or len(route_coordinates) < 2:
        return None, None
    
    # CRITICAL FIX: Always calculate cumulative distances from lat/lon using Haversine
    # IGNORE distance_m attribute completely - it may be corrupted/incorrect
    # This ensures we use the physical reality of coordinates, not corrupted metadata
    cumulative_distance = 0.0
    route_points = []
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Polyline walker: Processing {len(route_coordinates)} route coordinates for target_distance={target_distance_m:.2f}m")
    
    for i, coord in enumerate(route_coordinates):
        lat = coord.get('lat')
        lon = coord.get('lon')
        
        # Skip if missing coordinates
        if lat is None or lon is None:
            logger.warning(f"Polyline walker: Skipping coord {i} - missing lat/lon")
            continue
        
        # CRITICAL: Always calculate cumulative distance from lat/lon using Haversine
        # Start at 0.0 for first point
        if i == 0:
            cumulative_distance = 0.0
        else:
            # Calculate segment length from previous point to current point
            prev_lat = route_points[-1]['lat']
            prev_lon = route_points[-1]['lon']
            
            # Haversine formula to calculate actual physical distance
            dlat = math.radians(lat - prev_lat)
            dlon = math.radians(lon - prev_lon)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(prev_lat)) * math.cos(math.radians(lat)) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            segment_length = 6371000.0 * c  # Earth radius in meters
            cumulative_distance += segment_length
        
        route_points.append({
            'lat': lat,
            'lon': lon,
            'distance_m': cumulative_distance  # Store calculated cumulative distance
        })
    
    logger.info(f"Polyline walker: Processed {len(route_points)} points, total distance={cumulative_distance:.2f}m, target={target_distance_m:.2f}m")
    
    if len(route_points) < 2:
        logger.warning(f"Polyline walker: Only {len(route_points)} valid points, need at least 2")
        return None, None
    
    # Handle edge cases
    if target_distance_m <= 0.0:
        return route_points[0]['lat'], route_points[0]['lon']
    
    if target_distance_m >= route_points[-1]['distance_m']:
        return route_points[-1]['lat'], route_points[-1]['lon']
    
    # Walk along polyline segments
    accumulated_distance = 0.0
    
    for i in range(len(route_points) - 1):
        p1 = route_points[i]
        p2 = route_points[i + 1]
        
        # Calculate segment length
        segment_length = p2['distance_m'] - p1['distance_m']
        
        # Check if target distance falls within this segment
        if p1['distance_m'] <= target_distance_m <= p2['distance_m']:
            # Interpolate coordinates within this segment
            if segment_length == 0.0:
                # Duplicate point, return coordinates as-is
                return p1['lat'], p1['lon']
            
            # Calculate interpolation factor (0.0 to 1.0)
            t = (target_distance_m - p1['distance_m']) / segment_length
            
            # Linear interpolation of coordinates
            lat = p1['lat'] + t * (p2['lat'] - p1['lat'])
            lon = p1['lon'] + t * (p2['lon'] - p1['lon'])
            
            return lat, lon
    
    # Should never reach here, but return last point as fallback
    return route_points[-1]['lat'], route_points[-1]['lon']


def create_terrain_profile_from_coordinates(
    coordinates: List[Dict[str, Any]]
) -> List[TerrainPoint]:
    """
    Create terrain profile from route coordinates.
    
    Args:
        coordinates: List of {lat, lon, elevation_m, distance_m} or {lat, lon, elevation_m}
        
    Returns:
        List of TerrainPoint objects
    """
    profile = []
    cumulative_distance = 0.0
    
    for i, coord in enumerate(coordinates):
        distance = coord.get("distance_m")
        if distance is None:
            # Calculate distance from previous point if not provided
            if i > 0 and profile:
                # Approximate distance using lat/lon (Haversine would be more accurate)
                prev = profile[-1]
                if prev.latitude and prev.longitude and coord.get("lat") and coord.get("lon"):
                    # Simple approximation (not accurate for long distances)
                    lat_diff = abs(coord["lat"] - prev.latitude)
                    lon_diff = abs(coord["lon"] - prev.longitude)
                    # Rough approximation: 1 degree ≈ 111 km
                    distance_km = ((lat_diff + lon_diff) * 111.0) / 2.0
                    cumulative_distance += distance_km * 1000.0  # Convert to meters
                else:
                    cumulative_distance += 100.0  # Default 100m spacing
            distance = cumulative_distance
        
        point = TerrainPoint(
            distance_m=distance,
            elevation_m=coord.get("elevation_m", 0.0),
            latitude=coord.get("lat"),
            longitude=coord.get("lon"),
        )
        profile.append(point)
        cumulative_distance = distance
    
    return profile

