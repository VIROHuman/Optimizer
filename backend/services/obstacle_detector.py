"""
Obstacle Detector Service.

Detects obstacles along the route (rivers, highways, steep slopes) and provides
safe spot finding with automatic nudge logic.
"""

import math
import requests
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from auto_spotter import TerrainPoint
from shapely.geometry import LineString, Point, Polygon

logger = logging.getLogger(__name__)


@dataclass
class ForbiddenZone:
    """Represents a forbidden zone where towers cannot be placed."""
    start_distance_m: float
    end_distance_m: float
    zone_type: str  # 'river', 'highway', 'steep_slope', 'waterway', 'water', 'wetland'
    name: Optional[str] = None  # e.g., 'Ganges River', 'NH-1', 'Canal', 'Pond'
    geometry: Optional[List[Dict[str, float]]] = None  # List of {lat, lon} points for visualization
    metadata: Optional[Dict[str, Any]] = None  # Additional info (width, waterway_type, etc.)


class ConstraintError(Exception):
    """Raised when no safe spot can be found within max_shift."""
    pass


class ObstacleDetector:
    """
    Detects obstacles along route and provides safe spot finding.
    
    Features:
    - OSM Query for highways, waterways, natural=water
    - Slope analysis for terrain > 30%
    - Smart nudge logic to find safe spots
    """
    
    OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
    MAX_SLOPE_PERCENT = 30.0  # 30% slope threshold
    DEFAULT_NUDGE_STEP = 5.0  # Search in 5m increments
    MIN_WATERWAY_BUFFER = 5.0  # Minimum buffer for narrow waterways (drains, ditches) in meters
    
    def __init__(
        self,
        route_coordinates: List[Dict[str, Any]],
        terrain_profile: List[TerrainPoint],
    ):
        """
        Initialize obstacle detector.
        
        Args:
            route_coordinates: List of route points with lat/lon
            terrain_profile: Terrain elevation profile
        """
        self.route_coordinates = route_coordinates
        self.terrain_profile = terrain_profile
        self.forbidden_zones: List[ForbiddenZone] = []
        
        # Detect obstacles
        self._detect_osm_obstacles()
        self._detect_steep_slopes()
        
        logger.info(f"Obstacle detector initialized with {len(self.forbidden_zones)} forbidden zones")
    
    def _detect_osm_obstacles(self) -> None:
        """
        Query OpenStreetMap for obstacles (highways, waterways, natural=water).
        
        Uses Overpass API to fetch features within route bounding box.
        """
        if not self.route_coordinates or len(self.route_coordinates) < 2:
            logger.warning("Insufficient route coordinates for OSM query")
            return
        
        # Calculate bounding box
        lats = [coord.get('lat') for coord in self.route_coordinates if coord.get('lat') is not None]
        lons = [coord.get('lon') for coord in self.route_coordinates if coord.get('lon') is not None]
        
        if not lats or not lons:
            logger.warning("No valid coordinates for OSM query")
            return
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        # Add buffer (0.01 degrees ≈ 1.1 km)
        buffer = 0.01
        bbox = f"{min_lat - buffer},{min_lon - buffer},{max_lat + buffer},{max_lon + buffer}"
        
        # Broad-Spectrum OSM Query: All water features + major roads
        # Flowing Water: river, canal, drain, ditch, stream
        # Standing Water: natural=water, landuse=reservoir, landuse=basin
        # Wetlands: natural=wetland
        # Major Roads: motorway, trunk, primary, secondary, tertiary
        query = f"""
        [out:json][timeout:25];
        (
          // Flowing Water
          way["waterway"~"^(river|canal|drain|ditch|stream)$"]({bbox});
          
          // Standing Water (ways and relations)
          relation["natural"="water"]({bbox});
          way["natural"="water"]({bbox});
          way["landuse"="reservoir"]({bbox});
          way["landuse"="basin"]({bbox});
          
          // Wetlands
          way["natural"="wetland"]({bbox});
          
          // Major Roads (including tertiary for important local roads)
          way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]({bbox});
        );
        out geom;
        """
        
        try:
            logger.info(f"Querying OSM Overpass API for obstacles in bbox: {bbox}")
            response = requests.post(
                self.OVERPASS_API_URL,
                data={'data': query},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Process OSM features (ways and relations)
            if 'elements' in data:
                for element in data['elements']:
                    element_type = element.get('type')
                    if element_type in ['way', 'relation'] and 'geometry' in element:
                        self._process_osm_feature(element)
            
            water_obstacles = len([z for z in self.forbidden_zones if z.zone_type in ['waterway', 'water', 'wetland']])
            road_obstacles = len([z for z in self.forbidden_zones if z.zone_type == 'highway'])
            logger.info(f"OSM query completed: {water_obstacles} water features, {road_obstacles} roads found")
        
        except requests.exceptions.RequestException as e:
            logger.warning(f"OSM query failed: {e}. Continuing without OSM obstacles.")
        except Exception as e:
            logger.error(f"Error processing OSM data: {e}")
    
    def _process_osm_feature(self, element: Dict[str, Any]) -> None:
        """
        Process an OSM feature and create forbidden zones.
        
        Args:
            element: OSM element with geometry (way or relation)
        """
        tags = element.get('tags', {})
        geometry = element.get('geometry', [])
        
        # Determine zone type and name
        zone_type = None
        name = None
        waterway_type = None
        
        if 'highway' in tags:
            zone_type = 'highway'
            name = tags.get('name') or tags.get('ref') or f"Highway ({tags.get('highway', 'unknown')})"
        elif 'waterway' in tags:
            waterway_type = tags.get('waterway', 'unknown')
            zone_type = 'waterway'
            name = tags.get('name') or f"Waterway ({waterway_type})"
        elif tags.get('natural') == 'water':
            zone_type = 'water'
            name = tags.get('name') or 'Water Body'
        elif tags.get('natural') == 'wetland':
            zone_type = 'wetland'
            name = tags.get('name') or 'Wetland'
        elif tags.get('landuse') in ['reservoir', 'basin']:
            zone_type = 'water'
            name = tags.get('name') or f"{tags.get('landuse', 'Water Body').title()}"
        
        if not zone_type or not geometry:
            return
        
        # Convert OSM geometry to route distance coordinates
        # Find intersections with route using shapely
        route_intersections = self._find_route_intersections_shapely(geometry, zone_type, waterway_type)
        
        if route_intersections:
            for start_dist, end_dist in route_intersections:
                # Extract geometry points for visualization
                geom_points = [{'lat': point.get('lat'), 'lon': point.get('lon')} 
                              for point in geometry if point.get('lat') and point.get('lon')]
                
                zone = ForbiddenZone(
                    start_distance_m=start_dist,
                    end_distance_m=end_dist,
                    zone_type=zone_type,
                    name=name,
                    geometry=geom_points if geom_points else None,
                    metadata={
                        'osm_id': element.get('id'),
                        'tags': tags,
                        'waterway_type': waterway_type,
                    }
                )
                self.forbidden_zones.append(zone)
                logger.debug(f"Created {zone_type} zone: {name} from {start_dist:.1f}m to {end_dist:.1f}m")
    
    def _find_route_intersections_shapely(
        self,
        obstacle_geometry: List[Dict[str, float]],
        zone_type: str,
        waterway_type: Optional[str] = None
    ) -> List[Tuple[float, float]]:
        """
        Find where obstacle geometry intersects with route using shapely.
        
        Uses proper geometric intersection detection for accurate results.
        Applies minimum buffer for narrow waterways (drains, ditches).
        
        Args:
            obstacle_geometry: List of {lat, lon} points from OSM
            zone_type: Type of obstacle ('waterway', 'water', 'highway', etc.)
            waterway_type: Specific waterway type if applicable (e.g., 'drain', 'ditch')
            
        Returns:
            List of (start_dist, end_dist) tuples
        """
        if not obstacle_geometry or len(obstacle_geometry) < 2:
            return []
        
        # Build route LineString
        route_points = []
        route_distances = []
        for coord in self.route_coordinates:
            lat = coord.get('lat')
            lon = coord.get('lon')
            dist = coord.get('distance_m', 0.0)
            if lat is not None and lon is not None:
                route_points.append((lon, lat))  # shapely uses (x, y) = (lon, lat)
                route_distances.append(dist)
        
        if len(route_points) < 2:
            return []
        
        route_line = LineString(route_points)
        
        # Build obstacle geometry
        obs_points = []
        for point in obstacle_geometry:
            lat = point.get('lat')
            lon = point.get('lon')
            if lat is not None and lon is not None:
                obs_points.append((lon, lat))
        
        if len(obs_points) < 2:
            return []
        
        # Create obstacle geometry (LineString for waterways/roads, Polygon for water bodies)
        if zone_type in ['water', 'wetland'] and len(obs_points) >= 3:
            # Try to create a polygon for water bodies
            try:
                obstacle_geom = Polygon(obs_points)
            except:
                # If polygon fails, use LineString
                obstacle_geom = LineString(obs_points)
        else:
            obstacle_geom = LineString(obs_points)
        
        # Determine buffer distance
        buffer_distance_deg = 0.0001  # ~11m at equator (default)
        
        # Apply minimum buffer for narrow waterways
        if zone_type == 'waterway' and waterway_type in ['drain', 'ditch']:
            # Minimum 5m buffer for drains/ditches (convert to degrees, ~0.000045 deg ≈ 5m)
            buffer_distance_deg = max(buffer_distance_deg, 0.000045)
        
        # Buffer the obstacle geometry
        try:
            buffered_obstacle = obstacle_geom.buffer(buffer_distance_deg)
        except:
            # Fallback if buffering fails
            buffered_obstacle = obstacle_geom
        
        # Find intersection
        try:
            intersection = route_line.intersection(buffered_obstacle)
        except:
            # Fallback to distance-based detection
            return self._find_route_intersections_fallback(obstacle_geometry, zone_type, waterway_type)
        
        if intersection.is_empty:
            return []
        
        # Convert intersection to route distances
        intersections = []
        
        if hasattr(intersection, 'geoms'):
            # MultiLineString or GeometryCollection
            for geom in intersection.geoms:
                if hasattr(geom, 'coords'):
                    for coord in geom.coords:
                        lon, lat = coord
                        route_dist = self._find_closest_route_distance(lon, lat, route_points, route_distances)
                        if route_dist is not None:
                            intersections.append(route_dist)
        elif hasattr(intersection, 'coords'):
            # Single LineString or Point
            for coord in intersection.coords:
                lon, lat = coord
                route_dist = self._find_closest_route_distance(lon, lat, route_points, route_distances)
                if route_dist is not None:
                    intersections.append(route_dist)
        
        if not intersections:
            return []
        
        # Create distance ranges from intersection points
        intersections.sort()
        min_dist = min(intersections)
        max_dist = max(intersections)
        
        # Add buffer (25m on each side, converted to distance along route)
        buffer_m = 25.0
        start_dist = max(0, min_dist - buffer_m)
        end_dist = max_dist + buffer_m
        
        return [(start_dist, end_dist)]
    
    def _find_closest_route_distance(
        self,
        lon: float,
        lat: float,
        route_points: List[Tuple[float, float]],
        route_distances: List[float]
    ) -> Optional[float]:
        """Find closest route distance for a given point."""
        if not route_points or not route_distances:
            return None
        
        point = Point(lon, lat)
        min_dist = float('inf')
        closest_idx = 0
        
        for i, route_point in enumerate(route_points):
            route_pt = Point(route_point)
            dist = point.distance(route_pt)
            if dist < min_dist:
                min_dist = dist
                closest_idx = i
        
        if closest_idx < len(route_distances):
            return route_distances[closest_idx]
        return None
    
    def _find_route_intersections_fallback(
        self,
        obstacle_geometry: List[Dict[str, float]],
        zone_type: str,
        waterway_type: Optional[str] = None
    ) -> List[Tuple[float, float]]:
        """
        Fallback intersection detection using distance-based method.
        
        Used when shapely operations fail.
        """
        if not obstacle_geometry or len(obstacle_geometry) < 2:
            return []
        
        intersections = []
        buffer_m = 50.0  # Default buffer
        
        # Apply minimum buffer for narrow waterways
        if zone_type == 'waterway' and waterway_type in ['drain', 'ditch']:
            buffer_m = max(buffer_m, self.MIN_WATERWAY_BUFFER * 10)  # Convert to distance-based buffer
        
        # For each segment of obstacle geometry, find closest route points
        for i in range(len(obstacle_geometry) - 1):
            obs_start = obstacle_geometry[i]
            obs_end = obstacle_geometry[i + 1]
            
            if not (obs_start.get('lat') and obs_start.get('lon') and 
                    obs_end.get('lat') and obs_end.get('lon')):
                continue
            
            # Find closest route points to this obstacle segment
            min_dist = float('inf')
            max_dist = 0.0
            found_intersection = False
            
            for route_coord in self.route_coordinates:
                route_lat = route_coord.get('lat')
                route_lon = route_coord.get('lon')
                
                if route_lat is None or route_lon is None:
                    continue
                
                # Calculate distance from route point to obstacle segment
                dist_to_segment = self._point_to_segment_distance(
                    route_lat, route_lon,
                    obs_start['lat'], obs_start['lon'],
                    obs_end['lat'], obs_end['lon']
                )
                
                # If within buffer, consider it an intersection
                if dist_to_segment < buffer_m:
                    found_intersection = True
                    route_dist = route_coord.get('distance_m', 0.0)
                    if route_dist < min_dist:
                        min_dist = route_dist
                    if route_dist > max_dist:
                        max_dist = route_dist
            
            if found_intersection and max_dist > min_dist:
                # Add buffer (25m on each side)
                intersections.append((max(0, min_dist - 25), max_dist + 25))
        
        # Merge overlapping intersections
        if intersections:
            intersections.sort()
            merged = []
            current_start, current_end = intersections[0]
            
            for start, end in intersections[1:]:
                if start <= current_end:
                    current_end = max(current_end, end)
                else:
                    merged.append((current_start, current_end))
                    current_start, current_end = start, end
            merged.append((current_start, current_end))
            return merged
        
        return []
    
    def _point_to_segment_distance(
        self,
        px: float, py: float,
        x1: float, y1: float,
        x2: float, y2: float
    ) -> float:
        """
        Calculate distance from point to line segment (Haversine approximation).
        
        Args:
            px, py: Point coordinates (lat, lon)
            x1, y1: Segment start (lat, lon)
            x2, y2: Segment end (lat, lon)
            
        Returns:
            Distance in meters
        """
        # Convert to approximate meters
        R = 6371000.0  # Earth radius in meters
        
        def haversine_dist(lat1, lon1, lat2, lon2):
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            return R * 2 * math.asin(math.sqrt(a))
        
        # Distance from point to segment endpoints
        dist1 = haversine_dist(px, py, x1, y1)
        dist2 = haversine_dist(px, py, x2, y2)
        seg_length = haversine_dist(x1, y1, x2, y2)
        
        if seg_length < 0.001:
            return dist1
        
        # Project point onto segment
        # Simplified: use closest endpoint if segment is short
        if seg_length < 100:  # Less than 100m
            return min(dist1, dist2)
        
        # For longer segments, approximate perpendicular distance
        return min(dist1, dist2, dist1 * 0.5)  # Conservative estimate
    
    def _detect_steep_slopes(self) -> None:
        """
        Analyze terrain profile for slopes > 30%.
        
        Marks segments with excessive slope as forbidden zones.
        """
        if not self.terrain_profile or len(self.terrain_profile) < 2:
            return
        
        steep_segments = []
        current_segment_start = None
        
        for i in range(len(self.terrain_profile) - 1):
            point1 = self.terrain_profile[i]
            point2 = self.terrain_profile[i + 1]
            
            dist = point2.distance_m - point1.distance_m
            if dist <= 0:
                continue
            
            elevation_diff = point2.elevation_m - point1.elevation_m
            slope_percent = abs(elevation_diff / dist) * 100.0
            
            if slope_percent > self.MAX_SLOPE_PERCENT:
                if current_segment_start is None:
                    current_segment_start = point1.distance_m
            else:
                if current_segment_start is not None:
                    # End of steep segment
                    steep_segments.append((current_segment_start, point1.distance_m))
                    current_segment_start = None
        
        # Handle segment that extends to end
        if current_segment_start is not None:
            steep_segments.append((current_segment_start, self.terrain_profile[-1].distance_m))
        
        # Create forbidden zones for steep slopes
        for start_dist, end_dist in steep_segments:
            # Get geometry points for this segment
            geom_points = []
            for point in self.terrain_profile:
                if start_dist <= point.distance_m <= end_dist:
                    if point.latitude and point.longitude:
                        geom_points.append({'lat': point.latitude, 'lon': point.longitude})
            
            zone = ForbiddenZone(
                start_distance_m=start_dist,
                end_distance_m=end_dist,
                zone_type='steep_slope',
                name=f"Steep Slope ({self.MAX_SLOPE_PERCENT}%+)",
                geometry=geom_points if geom_points else None,
                metadata={
                    'slope_percent': '>30%',
                    'unbuildable': True,
                }
            )
            self.forbidden_zones.append(zone)
            logger.debug(f"Created steep_slope zone from {start_dist:.1f}m to {end_dist:.1f}m")
    
    def get_safe_spot(
        self,
        target_distance: float,
        max_shift: float = 100.0
    ) -> float:
        """
        Find safe spot near target distance, nudging if necessary.
        
        Logic:
        1. Check if target_distance is inside a forbidden zone
        2. If safe: return target_distance
        3. If forbidden: search outwards (±5m, ±10m, etc.) up to max_shift
        4. Return nearest safe distance
        
        Args:
            target_distance: Proposed tower distance along route
            max_shift: Maximum distance to search (meters)
            
        Returns:
            Safe distance along route
            
        Raises:
            ConstraintError: If no safe spot found within max_shift
        """
        # Check if target is in any forbidden zone
        if not self._is_in_forbidden_zone(target_distance):
            return target_distance
        
        # Find which zone we're in
        conflicting_zone = self._get_conflicting_zone(target_distance)
        zone_type = conflicting_zone.zone_type if conflicting_zone else 'unknown'
        obstacle_name = conflicting_zone.name if conflicting_zone else 'obstacle'
        
        # Search outwards for safe spot
        for shift in range(int(self.DEFAULT_NUDGE_STEP), int(max_shift) + 1, int(self.DEFAULT_NUDGE_STEP)):
            # Try forward
            forward_pos = target_distance + shift
            if not self._is_in_forbidden_zone(forward_pos):
                logger.warning(f"[NUDGE] Moved tower at {target_distance:.1f}m to {forward_pos:.1f}m to avoid {obstacle_name} ({zone_type})")
                return forward_pos
            
            # Try backward
            backward_pos = target_distance - shift
            if backward_pos >= 0 and not self._is_in_forbidden_zone(backward_pos):
                logger.warning(f"[NUDGE] Moved tower at {target_distance:.1f}m to {backward_pos:.1f}m to avoid {obstacle_name} ({zone_type})")
                return backward_pos
        
        # No safe spot found
        raise ConstraintError(
            f"No safe spot found within {max_shift}m of {target_distance:.1f}m "
            f"(conflicting with {zone_type})"
        )
    
    def _is_in_forbidden_zone(self, distance: float) -> bool:
        """Check if distance is inside any forbidden zone."""
        for zone in self.forbidden_zones:
            if zone.start_distance_m <= distance <= zone.end_distance_m:
                return True
        return False
    
    def _get_conflicting_zone(self, distance: float) -> Optional[ForbiddenZone]:
        """Get the forbidden zone that conflicts with this distance."""
        for zone in self.forbidden_zones:
            if zone.start_distance_m <= distance <= zone.end_distance_m:
                return zone
        return None
    
    def get_obstacles_for_visualization(self) -> List[Dict[str, Any]]:
        """
        Get obstacles formatted for frontend visualization.
        
        Returns:
            List of obstacle dictionaries with geometry and metadata
        """
        obstacles = []
        for zone in self.forbidden_zones:
            obstacles.append({
                'start_distance_m': zone.start_distance_m,
                'end_distance_m': zone.end_distance_m,
                'type': zone.zone_type,
                'name': zone.name,
                'geometry': zone.geometry or [],
                'metadata': zone.metadata or {},
            })
        return obstacles

