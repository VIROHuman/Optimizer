"""
Section-Based Tower Placement Module.

Implements the 4-phase section-based tower placement algorithm:
1. Route Pre-Processing (Corner Merging)
2. Define Sections
3. Optimize Spans (With Slack Logic)
4. Precise Placement (Vector Math)
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from auto_spotter import TerrainPoint, TowerPosition, AutoSpotter
from data_models import OptimizationInputs
import logging
from backend.services.obstacle_detector import ConstraintError

logger = logging.getLogger(__name__)


@dataclass
class RouteCorner:
    """A corner point in the route."""
    index: int
    lat: float
    lon: float
    elevation_m: float
    distance_m: float  # Cumulative distance from start


@dataclass
class RouteSection:
    """A logical section of the route between two corners."""
    section_index: int
    start_corner: RouteCorner
    end_corner: RouteCorner
    section_length_m: float
    is_first: bool = False
    is_last: bool = False


class SectionBasedPlacer:
    """
    Section-based tower placement with 4-phase algorithm.
    """
    
    CORNER_MERGE_THRESHOLD_M = 50.0  # Merge corners if segment < 50m
    SLACK_SPAN_MIN_M = 150.0  # Minimum slack span for first/last sections
    SLACK_SPAN_MAX_M = 200.0  # Maximum slack span for first/last sections
    SLACK_FORCE_DISTANCE_M = 200.0  # Force first tower at ~200m for long sections
    
    def __init__(
        self,
        inputs: OptimizationInputs,
        max_span_m: float = 450.0,
        min_span_m: float = 250.0,
    ):
        """
        Initialize section-based placer.
        
        Args:
            inputs: OptimizationInputs with project context
            max_span_m: Maximum allowed span length
            min_span_m: Minimum allowed span length
        """
        self.inputs = inputs
        self.max_span_m = max_span_m
        self.min_span_m = min_span_m
        self.spotter = AutoSpotter(
            inputs=inputs,
            max_span_m=max_span_m,
            min_span_m=min_span_m,
        )
    
    def place_towers(
        self,
        route_coordinates: List[Dict[str, Any]],
        terrain_profile: List[TerrainPoint],
        route_start_lat: Optional[float] = None,
        route_start_lon: Optional[float] = None,
    ) -> Tuple[List[TowerPosition], List[Dict[str, Any]]]:
        """
        Place towers using 4-phase section-based algorithm with obstacle detection.
        
        Args:
            route_coordinates: List of route points with lat/lon/elevation/distance
            terrain_profile: Terrain elevation profile
            route_start_lat: Optional starting latitude
            route_start_lon: Optional starting longitude
            
        Returns:
            Tuple of (tower_positions, obstacles) where obstacles is list for visualization
        """
        # Initialize obstacle detector
        from backend.services.obstacle_detector import ObstacleDetector
        detector = ObstacleDetector(
            route_coordinates=route_coordinates,
            terrain_profile=terrain_profile,
        )
        obstacles = detector.get_obstacles_for_visualization()
        logger.info(f"Obstacle detector initialized: {len(obstacles)} obstacles found")
        
        # Phase 1: Route Pre-Processing (Corner Merging)
        merged_corners = self._phase1_merge_corners(route_coordinates)
        logger.info(f"Phase 1: Merged {len(route_coordinates)} corners to {len(merged_corners)} after merging < {self.CORNER_MERGE_THRESHOLD_M}m segments")
        
        # Phase 2: Define Sections
        sections = self._phase2_define_sections(merged_corners)
        logger.info(f"Phase 2: Defined {len(sections)} sections from route")
        
        # Phase 3 & 4: Optimize spans and place towers for each section
        all_towers = []
        tower_index = 0
        
        for section in sections:
            # Phase 3: Optimize spans for this section
            span_info = self._phase3_optimize_spans(section)
            num_spans = span_info['num_spans']
            actual_span = span_info['actual_span']
            is_smart_slack = span_info.get('is_smart_slack', False)
            slack_target = span_info.get('slack_target', None)
            required_span_for_rest = span_info.get('required_span_for_rest', None)
            
            logger.info(
                f"Phase 3: Section {section.section_index} ({section.section_length_m:.1f}m) -> "
                f"{num_spans} spans, {'smart slack' if is_smart_slack else f'{actual_span:.1f}m each'}"
            )
            
            # Phase 4: Precise placement with vector math
            section_towers = self._phase4_precise_placement(
                section=section,
                num_spans=num_spans,
                actual_span=actual_span,
                terrain_profile=terrain_profile,
                route_start_lat=route_start_lat,
                route_start_lon=route_start_lon,
                route_coordinates=route_coordinates,
                start_tower_index=tower_index,
                is_smart_slack=is_smart_slack,
                slack_target=slack_target,
                required_span_for_rest=required_span_for_rest,
            )
            
            all_towers.extend(section_towers)
            tower_index += len(section_towers)
        
        # Apply obstacle-aware nudge logic to all towers
        nudged_towers = []
        for tower in all_towers:
            original_distance = tower.distance_along_route_m
            
            try:
                # Get safe spot (may nudge if in forbidden zone)
                safe_distance = detector.get_safe_spot(original_distance, max_shift=100.0)
                
                if safe_distance != original_distance:
                    # Tower was nudged
                    shift = safe_distance - original_distance
                    direction = "forward" if shift > 0 else "backward"
                    
                    # Find which obstacle caused the nudge
                    # Access the method through the detector's public interface
                    conflicting_zone = None
                    for zone in detector.forbidden_zones:
                        if zone.start_distance_m <= original_distance <= zone.end_distance_m:
                            conflicting_zone = zone
                            break
                    
                    obstacle_type = conflicting_zone.zone_type if conflicting_zone else 'obstacle'
                    # 1. Keep the Real Name (UTF-8)
                    obstacle_name = conflicting_zone.name if conflicting_zone else 'Unknown'
                    
                    tower.original_distance_m = original_distance
                    tower.distance_along_route_m = safe_distance
                    
                    # 2. Store Real Name for UI (React handles Chinese fine)
                    tower.nudge_description = f"Shifted {abs(shift):.1f}m {direction} to avoid {obstacle_name}"
                    
                    # 3. Log the Safe Name (Windows Console hates Chinese)
                    try:
                        # Try logging the real one first
                        logger.warning(
                            f"[NUDGE] Tower {tower.index} moved from {original_distance:.1f}m to {safe_distance:.1f}m "
                            f"due to {obstacle_type} ({obstacle_name})"
                        )
                    except UnicodeEncodeError:
                        # If it fails, log the sanitized version
                        safe_type = str(obstacle_type).encode('ascii', errors='replace').decode('ascii')
                        safe_name = str(obstacle_name).encode('ascii', errors='replace').decode('ascii')
                        logger.warning(
                            f"[NUDGE] Tower {tower.index} moved from {original_distance:.1f}m to {safe_distance:.1f}m "
                            f"due to {safe_type} ({safe_name})"
                        )
                else:
                    tower.nudge_description = None
                    tower.original_distance_m = None
                
            except Exception as e:
                # ConstraintError or other error - place tower anyway but flag as violation
                try:
                    safe_msg = str(e).encode('ascii', errors='replace').decode('ascii')
                    logger.error(
                        f"[VIOLATION] Tower {tower.index} at {original_distance:.1f}m: {safe_msg}. "
                        f"Placing anyway (fallback)."
                    )
                except Exception:
                    logger.error(
                        f"[VIOLATION] Tower {tower.index} at {original_distance:.1f}m: [encoding error]. "
                        f"Placing anyway (fallback)."
                    )
                tower.nudge_description = f"[ALERT] CONSTRAINT VIOLATION: {str(e)}"
                tower.original_distance_m = original_distance
            
            # Recalculate coordinates for nudged position
            if tower.distance_along_route_m != original_distance:
                # Get new coordinates for nudged position
                lat, lon = self.spotter._get_coordinates_at_distance(
                    tower.distance_along_route_m,
                    terrain_profile,
                    route_start_lat,
                    route_start_lon,
                    route_coordinates,
                )
                tower.latitude = lat
                tower.longitude = lon
                tower.elevation_m = self.spotter.interpolate_elevation(
                    tower.distance_along_route_m,
                    terrain_profile
                )
            
            nudged_towers.append(tower)
        
        # Validate tower sequencing
        self._validate_tower_sequencing(nudged_towers)
        
        logger.info(f"Section-based placer placed {len(nudged_towers)} towers total (with obstacle detection)")
        return nudged_towers, obstacles
    
    def _phase1_merge_corners(
        self,
        route_coordinates: List[Dict[str, Any]]
    ) -> List[RouteCorner]:
        """
        Phase 1: Route Pre-Processing (Corner Merging).
        
        Iterate through route_coordinates and merge consecutive corners
        if the segment between them is < 50m.
        
        Args:
            route_coordinates: List of route points
            
        Returns:
            List of merged RouteCorner objects
        """
        if not route_coordinates or len(route_coordinates) < 2:
            return []
        
        merged = []
        
        # Always include first corner
        first_coord = route_coordinates[0]
        first_corner = RouteCorner(
            index=0,
            lat=first_coord.get('lat', 0.0),
            lon=first_coord.get('lon', 0.0),
            elevation_m=first_coord.get('elevation_m', 0.0),
            distance_m=0.0,
        )
        merged.append(first_corner)
        
        # Calculate cumulative distances using Haversine
        cumulative_distance = 0.0
        
        for i in range(1, len(route_coordinates)):
            prev_coord = route_coordinates[i - 1]
            curr_coord = route_coordinates[i]
            
            # Calculate segment distance using Haversine
            segment_distance = self._haversine_distance(
                prev_coord.get('lat', 0.0),
                prev_coord.get('lon', 0.0),
                curr_coord.get('lat', 0.0),
                curr_coord.get('lon', 0.0),
            )
            cumulative_distance += segment_distance
            
            # Check if segment is < 50m (merge threshold)
            if segment_distance < self.CORNER_MERGE_THRESHOLD_M:
                # Skip this corner (merge with previous)
                logger.debug(
                    f"Merging corner {i}: segment {segment_distance:.1f}m < {self.CORNER_MERGE_THRESHOLD_M}m"
                )
                continue
            
            # Keep this corner
            corner = RouteCorner(
                index=len(merged),
                lat=curr_coord.get('lat', 0.0),
                lon=curr_coord.get('lon', 0.0),
                elevation_m=curr_coord.get('elevation_m', 0.0),
                distance_m=cumulative_distance,
            )
            merged.append(corner)
        
        # Always include last corner if it's not already included
        if merged and merged[-1].index < len(route_coordinates) - 1:
            last_coord = route_coordinates[-1]
            # Calculate final distance
            prev_corner = merged[-1]
            final_segment = self._haversine_distance(
                prev_corner.lat,
                prev_corner.lon,
                last_coord.get('lat', 0.0),
                last_coord.get('lon', 0.0),
            )
            final_distance = prev_corner.distance_m + final_segment
            
            last_corner = RouteCorner(
                index=len(merged),
                lat=last_coord.get('lat', 0.0),
                lon=last_coord.get('lon', 0.0),
                elevation_m=last_coord.get('elevation_m', 0.0),
                distance_m=final_distance,
            )
            merged.append(last_corner)
        
        return merged
    
    def _phase2_define_sections(
        self,
        corners: List[RouteCorner]
    ) -> List[RouteSection]:
        """
        Phase 2: Define Sections.
        
        Break the validated route into logical sections:
        Start → Corner 1, Corner 1 → Corner 2, etc.
        
        Args:
            corners: List of merged RouteCorner objects
            
        Returns:
            List of RouteSection objects
        """
        if len(corners) < 2:
            return []
        
        sections = []
        
        for i in range(len(corners) - 1):
            start_corner = corners[i]
            end_corner = corners[i + 1]
            
            # Calculate section length using Haversine
            section_length = self._haversine_distance(
                start_corner.lat,
                start_corner.lon,
                end_corner.lat,
                end_corner.lon,
            )
            
            section = RouteSection(
                section_index=i,
                start_corner=start_corner,
                end_corner=end_corner,
                section_length_m=section_length,
                is_first=(i == 0),
                is_last=(i == len(corners) - 2),
            )
            sections.append(section)
        
        return sections
    
    def _phase3_optimize_spans(
        self,
        section: RouteSection
    ) -> Dict[str, Any]:
        """
        Phase 3: Optimize Spans (With Smart Slack Logic & Aggressive Minimization).
        
        Special rules:
        - First & Last sections: Smart slack span logic (attempt 150m, fallback to standard)
        - Middle sections: Use min_towers strictly (no over-densification)
        
        Args:
            section: RouteSection to optimize
            
        Returns:
            Dict with num_spans, actual_span, and smart slack info
        """
        section_length = section.section_length_m
        
        # Smart Slack Span Logic for First & Last Sections
        if section.is_first or section.is_last:
            return self._smart_slack_span_logic(section_length, section.is_first, section.is_last)
        
        # Standard Rule for Middle Sections: Aggressive Minimization
        # CRITICAL: Use min_towers strictly. Do not increment to 'smooth' spans.
        min_towers = math.ceil(section_length / self.max_span_m)
        num_spans = min_towers
        actual_span = section_length / num_spans
        
        # Only reduce num_spans if mathematically impossible to avoid (actual_span < min_span)
        if actual_span < self.min_span_m and num_spans > 1:
            num_spans -= 1
            actual_span = section_length / num_spans
        
        return {
            'num_spans': num_spans,
            'actual_span': actual_span,
            'is_smart_slack': False,
        }
    
    def _smart_slack_span_logic(
        self,
        section_length: float,
        is_first: bool,
        is_last: bool
    ) -> Dict[str, Any]:
        """
        Smart Slack Span Logic: Attempt 150m terminal span with fallback.
        
        Algorithm:
        Step A: Calculate N (Min Spans) = ceil(L / max_span)
        Step B (Eligibility): If N <= 1, skip logic (use standard split)
        Step C (Attempt): Try to reserve slack_target = 150m
        Step D (Validation): Check if min_span <= required_span_for_rest <= max_span
        Step E (Outcome): If Valid: Create uneven split, else: Fallback to standard
        
        Args:
            section_length: Length of section in meters
            is_first: Whether this is the first section
            is_last: Whether this is the last section
            
        Returns:
            Dict with num_spans, actual_span, and smart slack info
        """
        slack_target = 150.0  # Target slack span for terminal
        
        # Step A: Calculate N (Min Spans)
        N = math.ceil(section_length / self.max_span_m)
        
        # Step B (Eligibility): If N <= 1, skip logic (use standard split)
        if N <= 1:
            # Standard single span
            return {
                'num_spans': 1,
                'actual_span': section_length,
                'is_smart_slack': False,
            }
        
        # Step C (Attempt): Try to reserve slack_target = 150m
        remaining_dist = section_length - slack_target
        
        # Need at least 1 span for remaining distance
        if remaining_dist <= 0:
            # Section too short, use standard
            return {
                'num_spans': 1,
                'actual_span': section_length,
                'is_smart_slack': False,
            }
        
        # Calculate required span for rest of section
        required_span_for_rest = remaining_dist / (N - 1)  # N-1 spans for remaining distance
        
        # Step D (Validation): Check if min_span <= required_span_for_rest <= max_span
        is_valid = (self.min_span_m <= required_span_for_rest <= self.max_span_m)
        
        # Step E (Outcome)
        if is_valid:
            # Valid: Create uneven split
            # First Section: [150, required_span, required_span...]
            # Last Section: [required_span, required_span..., 150]
            num_spans = N
            actual_span = section_length / num_spans  # Average for reference
            
            return {
                'num_spans': num_spans,
                'actual_span': actual_span,
                'is_smart_slack': True,
                'slack_target': slack_target,
                'required_span_for_rest': required_span_for_rest,
            }
        else:
            # Invalid (Fallback): Revert to safe standard behavior
            num_spans = N
            actual_span = section_length / num_spans
            
            # Validate actual_span is within bounds
            if actual_span < self.min_span_m and num_spans > 1:
                num_spans -= 1
                actual_span = section_length / num_spans
            
            return {
                'num_spans': num_spans,
                'actual_span': actual_span,
                'is_smart_slack': False,
            }
    
    def _phase4_precise_placement(
        self,
        section: RouteSection,
        num_spans: int,
        actual_span: float,
        terrain_profile: List[TerrainPoint],
        route_start_lat: Optional[float],
        route_start_lon: Optional[float],
        route_coordinates: List[Dict[str, Any]],
        start_tower_index: int,
        is_smart_slack: bool = False,
        slack_target: Optional[float] = None,
        required_span_for_rest: Optional[float] = None,
    ) -> List[TowerPosition]:
        """
        Phase 4: Precise Placement (Vector Math).
        
        - Anchors: Place tower exactly at section end (corner). Tag as 'anchor'.
        - Intermediates: Place num_spans - 1 towers interpolated between start and end.
          Tag as 'suspension'.
        
        Args:
            section: RouteSection to place towers in
            num_spans: Number of spans in this section
            actual_span: Actual span length
            terrain_profile: Terrain elevation profile
            route_start_lat: Optional starting latitude
            route_start_lon: Optional starting longitude
            route_coordinates: Full route coordinates for polyline walker
            start_tower_index: Starting tower index for this section
            
        Returns:
            List of TowerPosition objects with design_type tags
        """
        towers = []
        
        # Calculate unit vector from start to end corner
        start_lat = section.start_corner.lat
        start_lon = section.start_corner.lon
        end_lat = section.end_corner.lat
        end_lon = section.end_corner.lon
        
        # Convert lat/lon to approximate local coordinates (meters)
        # Use start corner as origin
        lat_origin = start_lat
        lon_origin = start_lon
        
        # Convert end corner to local coordinates
        dlat = (end_lat - lat_origin) * 111320.0  # meters per degree latitude
        dlon = (end_lon - lon_origin) * 111320.0 * math.cos(math.radians(lat_origin))
        
        # Calculate unit vector
        section_vector_length = math.sqrt(dlat**2 + dlon**2)
        if section_vector_length < 0.001:  # Very short section
            unit_vector = (0.0, 0.0)
        else:
            unit_vector = (dlon / section_vector_length, dlat / section_vector_length)
        
        # Place anchor at section start (if this is the first section, or if previous section didn't place it)
        # For non-first sections, the start corner is the end corner of previous section (already placed)
        if section.is_first:
            # Place anchor at section start
            start_elevation = self.spotter.interpolate_elevation(
                section.start_corner.distance_m,
                terrain_profile
            )
            start_lat, start_lon = self.spotter._get_coordinates_at_distance(
                section.start_corner.distance_m,
                terrain_profile,
                route_start_lat,
                route_start_lon,
                route_coordinates,
            )
            
            start_tower = TowerPosition(
                index=start_tower_index,
                distance_along_route_m=section.start_corner.distance_m,
                latitude=start_lat,
                longitude=start_lon,
                elevation_m=start_elevation,
                design_type='anchor',  # Tag as anchor
            )
            towers.append(start_tower)
            current_tower_index = start_tower_index + 1
        else:
            # Start corner is already placed by previous section
            current_tower_index = start_tower_index
        
        # Place intermediate towers (suspension) between start and end
        if is_smart_slack and slack_target is not None and required_span_for_rest is not None:
            # Smart slack span: Uneven split
            # First Section: [150, required_span, required_span...]
            # Last Section: [required_span, required_span..., 150]
            cumulative_distance = section.start_corner.distance_m
            
            if section.is_first:
                # First section: slack at start
                # First span is slack_target (150m)
                cumulative_distance += slack_target
                
                # Place remaining towers at required_span_for_rest intervals
                for span_index in range(1, num_spans):
                    distance_along_route = cumulative_distance
                    cumulative_distance += required_span_for_rest
                    
                    # Get elevation at this position
                    elevation = self.spotter.interpolate_elevation(distance_along_route, terrain_profile)
                    
                    # Get coordinates using polyline walker
                    lat, lon = self.spotter._get_coordinates_at_distance(
                        distance_along_route,
                        terrain_profile,
                        route_start_lat,
                        route_start_lon,
                        route_coordinates,
                    )
                    
                    intermediate_tower = TowerPosition(
                        index=current_tower_index,
                        distance_along_route_m=distance_along_route,
                        latitude=lat,
                        longitude=lon,
                        elevation_m=elevation,
                        design_type='suspension',  # Tag as suspension
                    )
                    towers.append(intermediate_tower)
                    current_tower_index += 1
            elif section.is_last:
                # Last section: slack at end
                # Place intermediate towers at required_span_for_rest intervals
                for span_index in range(1, num_spans):
                    cumulative_distance += required_span_for_rest
                    distance_along_route = cumulative_distance
                    
                    # Get elevation at this position
                    elevation = self.spotter.interpolate_elevation(distance_along_route, terrain_profile)
                    
                    # Get coordinates using polyline walker
                    lat, lon = self.spotter._get_coordinates_at_distance(
                        distance_along_route,
                        terrain_profile,
                        route_start_lat,
                        route_start_lon,
                        route_coordinates,
                    )
                    
                    intermediate_tower = TowerPosition(
                        index=current_tower_index,
                        distance_along_route_m=distance_along_route,
                        latitude=lat,
                        longitude=lon,
                        elevation_m=elevation,
                        design_type='suspension',  # Tag as suspension
                    )
                    towers.append(intermediate_tower)
                    current_tower_index += 1
            else:
                # Should not happen (smart slack only for first/last)
                # Fall through to standard logic
                pass
        
        # Standard placement: Uniform spans with jitter to avoid robotic placement
        if not (is_smart_slack and slack_target is not None and required_span_for_rest is not None):
            import random
            # Calculate cumulative distance with jitter applied
            cumulative_distance = section.start_corner.distance_m
            total_remaining_distance = section.section_length_m
            
            for span_index in range(1, num_spans):  # num_spans - 1 intermediate towers
                # Apply jitter factor (0.90 to 1.10) to make placement less robotic
                jitter = random.uniform(0.90, 1.10)
                
                # Calculate span with jitter
                span_with_jitter = actual_span * jitter
                
                # Ensure we don't exceed section bounds
                remaining_spans = num_spans - span_index
                if remaining_spans > 0:
                    # Adjust jitter if it would cause us to exceed section length
                    max_allowed_span = total_remaining_distance / remaining_spans * 1.1  # Allow 10% buffer
                    span_with_jitter = min(span_with_jitter, max_allowed_span)
                
                # Update cumulative distance
                cumulative_distance += span_with_jitter
                total_remaining_distance -= span_with_jitter
                
                # Use cumulative distance for position
                distance_along_route = cumulative_distance
            
                # Get elevation at this position
                elevation = self.spotter.interpolate_elevation(distance_along_route, terrain_profile)
                
                # Get coordinates using polyline walker
                lat, lon = self.spotter._get_coordinates_at_distance(
                    distance_along_route,
                    terrain_profile,
                    route_start_lat,
                    route_start_lon,
                    route_coordinates,
                )
                
                intermediate_tower = TowerPosition(
                    index=current_tower_index,
                    distance_along_route_m=distance_along_route,
                    latitude=lat,
                    longitude=lon,
                    elevation_m=elevation,
                    design_type='suspension',  # Tag as suspension
                )
                towers.append(intermediate_tower)
                current_tower_index += 1
        
        # Place anchor at section end (corner)
        end_elevation = self.spotter.interpolate_elevation(
            section.end_corner.distance_m,
            terrain_profile
        )
        end_lat, end_lon = self.spotter._get_coordinates_at_distance(
            section.end_corner.distance_m,
            terrain_profile,
            route_start_lat,
            route_start_lon,
            route_coordinates,
        )
        
        end_tower = TowerPosition(
            index=current_tower_index,
            distance_along_route_m=section.end_corner.distance_m,
            latitude=end_lat,
            longitude=end_lon,
            elevation_m=end_elevation,
            design_type='anchor',  # Tag as anchor
        )
        towers.append(end_tower)
        
        return towers
    
    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """
        Calculate distance between two points using Haversine formula.
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
            
        Returns:
            Distance in meters
        """
        R = 6371000.0  # Earth radius in meters
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (
            math.sin(dlat / 2) ** 2 +
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
            math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _validate_tower_sequencing(self, towers: List[TowerPosition]) -> None:
        """
        Validate that towers are in strict monotonic order.
        
        Args:
            towers: List of TowerPosition objects
        """
        if len(towers) < 2:
            return
        
        for i in range(1, len(towers)):
            prev_dist = towers[i - 1].distance_along_route_m
            curr_dist = towers[i].distance_along_route_m
            
            if curr_dist <= prev_dist:
                logger.warning(
                    f"Tower sequencing violation: Tower {i} at {curr_dist:.2f}m <= "
                    f"Tower {i-1} at {prev_dist:.2f}m"
                )
                # Fix by ensuring minimum span
                towers[i].distance_along_route_m = prev_dist + self.spotter.MIN_SPAN

