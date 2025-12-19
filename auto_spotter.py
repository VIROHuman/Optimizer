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
        self.min_span_m = min_span_m
        self.clearance_margin_m = clearance_margin_m
        self.step_back_m = step_back_m
    
    def calculate_sag(
        self,
        span_length_m: float,
        conductor_weight_per_m: float = 1.5,  # kg/m (typical ACSR)
        tension_kN: float = 50.0,  # Typical tension
    ) -> float:
        """
        Calculate conductor sag at mid-span.
        
        Uses catenary approximation:
        sag ≈ (weight × span²) / (8 × tension)
        
        Args:
            span_length_m: Span length in meters
            conductor_weight_per_m: Conductor weight per meter (kg/m)
            tension_kN: Conductor tension (kN)
            
        Returns:
            Sag at mid-span in meters
        """
        # Convert weight to force (N/m)
        weight_per_m_N = conductor_weight_per_m * 9.81  # kg/m to N/m
        
        # Convert tension to N
        tension_N = tension_kN * 1000.0
        
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
        
        # Get route end distance
        route_end_distance = terrain_profile[-1].distance_m if terrain_profile else 0.0
        
        while current_distance < route_end_distance:
            # Place tower at current position
            current_elevation = self.interpolate_elevation(current_distance, terrain_profile)
            
            # Get coordinates if available
            lat, lon = self._get_coordinates_at_distance(current_distance, terrain_profile, route_start_lat, route_start_lon)
            
            tower = TowerPosition(
                index=tower_index,
                distance_along_route_m=current_distance,
                latitude=lat,
                longitude=lon,
                elevation_m=current_elevation,
            )
            towers.append(tower)
            
            # Try to place next tower at max span
            next_distance = current_distance + self.max_span_m
            
            # If beyond route end, we're done
            if next_distance >= route_end_distance:
                # Place final tower at route end
                final_elevation = self.interpolate_elevation(route_end_distance, terrain_profile)
                final_lat, final_lon = self._get_coordinates_at_distance(
                    route_end_distance, terrain_profile, route_start_lat, route_start_lon
                )
                final_tower = TowerPosition(
                    index=tower_index + 1,
                    distance_along_route_m=route_end_distance,
                    latitude=final_lat,
                    longitude=final_lon,
                    elevation_m=final_elevation,
                )
                towers.append(final_tower)
                break
            
            # Check clearance for this span
            next_elevation = self.interpolate_elevation(next_distance, terrain_profile)
            next_lat, next_lon = self._get_coordinates_at_distance(
                next_distance, terrain_profile, route_start_lat, route_start_lon
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
                current_distance = next_distance
                tower_index += 1
            else:
                # Collision detected, step back
                current_distance = next_distance - self.step_back_m
                
                # Ensure we don't go below minimum span
                if current_distance - tower.distance_along_route_m < self.min_span_m:
                    # Can't step back further, place tower at minimum span
                    current_distance = tower.distance_along_route_m + self.min_span_m
                    tower_index += 1
                else:
                    # Continue trying
                    continue
        
        return towers
    
    def _get_coordinates_at_distance(
        self,
        distance_m: float,
        terrain_profile: List[TerrainPoint],
        route_start_lat: Optional[float],
        route_start_lon: Optional[float],
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Get coordinates at given distance along route.
        
        Args:
            distance_m: Distance from route start
            terrain_profile: Terrain profile (may contain lat/lon)
            route_start_lat: Starting latitude
            route_start_lon: Starting longitude
            
        Returns:
            Tuple of (latitude, longitude) or (None, None) if not available
        """
        # If terrain profile has coordinates, interpolate
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
                    return lat, lon
        
        # If no coordinates in profile, return None
        return None, None


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

