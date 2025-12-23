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
from data_models import OptimizationInputs, TowerDesign, FoundationType, TowerType
from pso_optimizer import get_base_width_ratio_for_tower_type


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
    selected_span_m: Optional[float] = None  # Actual span used to reach this tower
    span_selection_reason: Optional[str] = None  # Reason for span selection (e.g., "cheapest safe", "max span", "end-of-line")


@dataclass
class SpanCandidate:
    """Span candidate evaluation result."""
    span_length_m: float
    is_safe: bool
    required_tower_height_m: float
    required_base_width_m: float
    sag_m: float
    clearance_m: float
    total_cost: float
    safety_violations: List[str]
    cost_breakdown: Dict[str, float]
    
    def __lt__(self, other):
        """Compare by cost (for sorting)."""
        if not self.is_safe and other.is_safe:
            return False  # Unsafe is worse
        if self.is_safe and not other.is_safe:
            return True  # Safe is better
        return self.total_cost < other.total_cost


class AutoSpotter:
    """
    Automatic tower placement along route with adaptive span optimization.
    
    This module places towers based on:
    - Span candidate evaluation (300, 340, 380, 420, 450 m)
    - Terrain clearance requirements
    - Conductor sag calculations
    - Cost optimization (selects cheapest SAFE span)
    - Safety validation
    
    It integrates cost and safety evaluation to select optimal spans.
    """
    
    # CRITICAL FIX 1: Minimum span length for physical spacing
    # This prevents towers from being placed too close together
    MIN_SPAN = 30.0  # meters - absolute minimum physical spacing
    
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
        self.min_span_m = max(min_span_m, self.MIN_SPAN)  # Ensure min_span >= MIN_SPAN
        self.clearance_margin_m = clearance_margin_m
        self.step_back_m = step_back_m
        
        # Span candidates for adaptive optimization
        # Default candidates, can be customized
        self.span_candidates = [300.0, 340.0, 380.0, 420.0, 450.0]
        # Filter candidates to be within min/max bounds
        self.span_candidates = [
            s for s in self.span_candidates 
            if self.min_span_m <= s <= self.max_span_m
        ]
        if not self.span_candidates:
            # Fallback: use max_span if no candidates in range
            self.span_candidates = [self.max_span_m]
    
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
    
    def evaluate_span_candidate(
        self,
        span_length_m: float,
        from_tower: TowerPosition,
        to_distance_m: float,
        terrain_profile: List[TerrainPoint],
        codal_engine: Any,  # CodalEngine instance (avoid circular import)
    ) -> SpanCandidate:
        """
        Evaluate a span candidate for cost and safety.
        
        Args:
            span_length_m: Candidate span length
            from_tower: Tower at span start
            to_distance_m: Distance to next tower position
            terrain_profile: Terrain elevation profile
            codal_engine: CodalEngine instance for safety validation
            
        Returns:
            SpanCandidate with evaluation results
        """
        from cost_engine import calculate_cost_with_breakdown
        
        # Calculate sag
        sag_m = self.calculate_sag(span_length_m)
        
        # Get terrain elevation at mid-span
        mid_distance = (from_tower.distance_along_route_m + to_distance_m) / 2.0
        mid_elevation = self.interpolate_elevation(mid_distance, terrain_profile)
        
        # Get elevation at next tower position
        to_elevation = self.interpolate_elevation(to_distance_m, terrain_profile)
        
        # Calculate required tower height for clearance
        # Conductor height at mid-span = avg_tower_top - sag
        # Clearance = conductor_height - mid_elevation >= clearance_margin
        # Solving: avg_tower_top >= mid_elevation + sag + clearance_margin
        # Use average of from and to tower heights
        min_conductor_height = mid_elevation + sag_m + self.clearance_margin_m
        avg_ground_elevation = (from_tower.elevation_m + to_elevation) / 2.0
        required_avg_tower_height = min_conductor_height - avg_ground_elevation
        
        # Required tower height (use same height for both towers for simplicity)
        # Voltage-based minimum heights (from PSO optimizer)
        voltage_min_heights = {
            132: 25.0,
            220: 30.0,
            400: 40.0,
            765: 50.0,
            900: 55.0,
        }
        voltage = self.inputs.voltage_level
        min_height = 25.0  # Default minimum
        for v_level, h in sorted(voltage_min_heights.items()):
            if voltage >= v_level:
                min_height = h
        
        required_tower_height = max(required_avg_tower_height, min_height)
        
        # Create design for evaluation
        # Use suspension tower as default (most common)
        tower_type = TowerType.SUSPENSION
        
        # Enforce geometry-coupled base width constraint using tower-type-specific ratio
        tower_type_ratio = get_base_width_ratio_for_tower_type(tower_type)
        required_base_width = max(required_tower_height * tower_type_ratio, 8.0)  # Minimum 8m base
        design = TowerDesign(
            tower_type=tower_type,
            tower_height=required_tower_height,
            base_width=required_base_width,
            span_length=span_length_m,
            foundation_type=FoundationType.PAD_FOOTING,
            footing_length=5.0,  # Conservative estimate
            footing_width=5.0,
            footing_depth=3.0,
        )
        
        # Validate safety
        safety_result = codal_engine.is_design_safe(design, self.inputs)
        
        # Calculate cost
        total_cost = 0.0
        cost_breakdown = {}
        if safety_result.is_safe:
            total_cost, cost_breakdown = calculate_cost_with_breakdown(design, self.inputs)
        else:
            # Unsafe design gets very high cost
            total_cost = 1e10
            cost_breakdown = {
                'steel_cost': 0.0,
                'foundation_cost': 0.0,
                'erection_cost': 0.0,
                'transport_cost': 0.0,
                'land_cost': 0.0,
                'total_cost': total_cost,
            }
        
        # Calculate actual clearance
        avg_tower_top = avg_ground_elevation + required_tower_height
        conductor_height = avg_tower_top - sag_m
        clearance = conductor_height - mid_elevation
        
        return SpanCandidate(
            span_length_m=span_length_m,
            is_safe=safety_result.is_safe and clearance >= self.clearance_margin_m,
            required_tower_height_m=required_tower_height,
            required_base_width_m=required_base_width,
            sag_m=sag_m,
            clearance_m=clearance,
            total_cost=total_cost,
            safety_violations=safety_result.violations,
            cost_breakdown=cost_breakdown,
        )
    
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
        codal_engine=None,
    ) -> List[TowerPosition]:
        """
        Place towers along route with adaptive span optimization.
        
        Algorithm:
        1. Start at route start (Tower 0)
        2. Evaluate span candidates: [300, 340, 380, 420, 450] m
        3. For each candidate: compute sag, clearance, required height, cost, safety
        4. Select cheapest SAFE span candidate
        5. Place tower at selected span
        6. Handle end-of-line: if remaining < 2*min_span, divide equally
        7. Repeat until route ends
        
        Args:
            terrain_profile: Terrain elevation profile
            route_start_lat: Optional starting latitude
            route_start_lon: Optional starting longitude
            codal_engine: CodalEngine instance for safety validation (required for span optimization)
            
        Returns:
            List of TowerPosition objects with selected span info
        """
        if not terrain_profile:
            return []
        
        # If no codal_engine provided, fall back to simple placement (backward compatibility)
        if codal_engine is None:
            return self._place_towers_simple(terrain_profile, route_start_lat, route_start_lon)
        
        towers: List[TowerPosition] = []
        
        # Start at route beginning
        current_distance = 0.0
        tower_index = 0
        
        # Get route end distance
        route_end_distance = terrain_profile[-1].distance_m if terrain_profile else 0.0
        
        while current_distance < route_end_distance:
            # Calculate remaining distance BEFORE placing tower
            remaining_distance = route_end_distance - current_distance
            
            # CRITICAL FIX 3: If remaining distance is less than MIN_SPAN, do NOT place a new tower
            # Extend previous span instead (if there's a previous tower)
            if remaining_distance < self.MIN_SPAN:
                # Do NOT place a new tower - extend previous span
                # If we have at least one tower, the last tower's span will extend to route end
                if towers:
                    # Update last tower's span to extend to route end
                    last_tower = towers[-1]
                    extended_span = route_end_distance - last_tower.distance_along_route_m
                    if extended_span >= self.MIN_SPAN:
                        # Place final tower at route end
                        final_elevation = self.interpolate_elevation(route_end_distance, terrain_profile)
                        final_lat, final_lon = self._get_coordinates_at_distance(
                            route_end_distance, terrain_profile, route_start_lat, route_start_lon
                        )
                        final_tower = TowerPosition(
                            index=tower_index,
                            distance_along_route_m=route_end_distance,
                            latitude=final_lat,
                            longitude=final_lon,
                            elevation_m=final_elevation,
                            selected_span_m=extended_span,
                            span_selection_reason=f"end-of-line: extended span {extended_span:.1f}m (remaining {remaining_distance:.1f}m < MIN_SPAN {self.MIN_SPAN:.1f}m)",
                        )
                        towers.append(final_tower)
                # Stop placement - cannot place more towers
                break
            
            # CRITICAL FIX 1: Enforce minimum span from last tower
            if towers:
                last_tower_distance = towers[-1].distance_along_route_m
                min_required_distance = last_tower_distance + self.MIN_SPAN
                if current_distance < min_required_distance:
                    # Current position violates minimum span, advance to minimum required
                    current_distance = min_required_distance
                    # If this exceeds route end, stop placement
                    if current_distance >= route_end_distance:
                        break
            
            # Place tower at current position
            current_elevation = self.interpolate_elevation(current_distance, terrain_profile)
            
            # Get coordinates if available
            lat, lon = self._get_coordinates_at_distance(current_distance, terrain_profile, route_start_lat, route_start_lon)
            
            tower = TowerPosition(
                index=tower_index,
                distance_along_route_m=current_distance,  # CRITICAL FIX 4: Full precision float, no rounding
                latitude=lat,
                longitude=lon,
                elevation_m=current_elevation,
            )
            towers.append(tower)
            
            # Recalculate remaining distance after placing tower
            remaining_distance = route_end_distance - current_distance
            
            # END-OF-LINE HANDLING: If remaining < 2 * min_span, divide equally
            if remaining_distance < 2.0 * self.min_span_m and remaining_distance >= self.min_span_m:
                # Divide remainder into 2 equal spans (don't do 450m + 50m, do 250m + 250m)
                num_remaining_towers = 2
                equal_span = remaining_distance / num_remaining_towers
                
                # Ensure each span is at least min_span
                if equal_span < self.min_span_m:
                    # If equal division gives spans < min_span, just place one tower at end
                    # This handles cases where remaining is between min_span and 2*min_span
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
                        selected_span_m=remaining_distance,
                        span_selection_reason=f"end-of-line: single span {remaining_distance:.1f}m (too small to divide)",
                    )
                    towers.append(final_tower)
                    break
                
                # Place remaining towers at equal spans
                last_placed_distance = current_distance
                for i in range(1, num_remaining_towers + 1):  # +1 to include final tower
                    next_distance = current_distance + equal_span * i
                    # Ensure we don't exceed route end
                    if next_distance >= route_end_distance:
                        next_distance = route_end_distance
                    
                    # CRITICAL FIX 1: Calculate actual span from last placed tower
                    actual_span = next_distance - last_placed_distance
                    
                    # CRITICAL FIX 1: Enforce minimum span - skip if too small
                    if actual_span < self.MIN_SPAN:
                        continue
                    
                    # CRITICAL FIX 1: Skip if this tower would violate minimum span from last placed tower
                    if towers and (next_distance - towers[-1].distance_along_route_m) < self.MIN_SPAN:
                        continue
                    
                    next_elevation = self.interpolate_elevation(next_distance, terrain_profile)
                    next_lat, next_lon = self._get_coordinates_at_distance(
                        next_distance, terrain_profile, route_start_lat, route_start_lon
                    )
                    next_tower = TowerPosition(
                        index=tower_index + i,
                        distance_along_route_m=next_distance,  # CRITICAL FIX 4: Full precision float
                        latitude=next_lat,
                        longitude=next_lon,
                        elevation_m=next_elevation,
                        selected_span_m=actual_span,  # Use actual span, not equal_span
                        span_selection_reason=f"end-of-line: divided {remaining_distance:.1f}m into {num_remaining_towers} equal spans ({equal_span:.1f}m each)",
                    )
                    towers.append(next_tower)
                    last_placed_distance = next_distance
                break
            
            # Filter span candidates that fit within remaining distance
            feasible_candidates = [
                s for s in self.span_candidates 
                if s <= remaining_distance
            ]
            
            if not feasible_candidates:
                # No candidate fits, use maximum possible span
                feasible_candidates = [min(remaining_distance, self.max_span_m)]
            
            # Evaluate each span candidate
            candidates = []
            for span_candidate in feasible_candidates:
                next_distance = current_distance + span_candidate
                candidate = self.evaluate_span_candidate(
                    span_length_m=span_candidate,
                    from_tower=tower,
                    to_distance_m=next_distance,
                    terrain_profile=terrain_profile,
                    codal_engine=codal_engine,
                )
                candidates.append(candidate)
            
            # Select cheapest SAFE span candidate
            safe_candidates = [c for c in candidates if c.is_safe]
            
            if safe_candidates:
                # Sort by cost (cheapest first)
                safe_candidates.sort(key=lambda x: x.total_cost)
                selected = safe_candidates[0]
                selected_span = selected.span_length_m
                reason = f"cheapest safe span (${selected.total_cost:.0f})"
                
                # If not max span, add reason
                if selected_span < self.max_span_m:
                    max_candidate = next((c for c in candidates if c.span_length_m == self.max_span_m), None)
                    if max_candidate and max_candidate.is_safe:
                        reason += f" (max span ${max_candidate.total_cost:.0f} was more expensive)"
                    elif max_candidate and not max_candidate.is_safe:
                        reason += f" (max span was unsafe)"
            else:
                # No safe candidates, use shortest candidate (will be marked unsafe later)
                candidates.sort(key=lambda x: x.span_length_m)
                selected = candidates[0]
                selected_span = selected.span_length_m
                reason = f"no safe candidates, using shortest ({selected.span_length_m}m)"
            
            # Place next tower at selected span
            next_distance = current_distance + selected_span
            
            # CRITICAL FIX 1: Enforce minimum span constraint
            min_required_distance = current_distance + self.MIN_SPAN
            if next_distance < min_required_distance:
                next_distance = min_required_distance
            
            # CRITICAL FIX 3: If remaining distance < MIN_SPAN, do NOT place new tower
            remaining_after_next = route_end_distance - next_distance
            if remaining_after_next < self.MIN_SPAN and next_distance < route_end_distance:
                # Cannot place another tower after this one, place final tower at route end
                actual_span = route_end_distance - current_distance
                if actual_span >= self.MIN_SPAN:
                    # Check if we already have a tower at route end
                    if not towers or abs(towers[-1].distance_along_route_m - route_end_distance) >= self.MIN_SPAN:
                        final_elevation = self.interpolate_elevation(route_end_distance, terrain_profile)
                        final_lat, final_lon = self._get_coordinates_at_distance(
                            route_end_distance, terrain_profile, route_start_lat, route_start_lon
                        )
                        final_tower = TowerPosition(
                            index=tower_index + 1,
                            distance_along_route_m=route_end_distance,  # CRITICAL FIX 4: Full precision
                            latitude=final_lat,
                            longitude=final_lon,
                            elevation_m=final_elevation,
                            selected_span_m=actual_span,
                            span_selection_reason=f"end-of-line: final span {actual_span:.1f}m (remaining {remaining_after_next:.1f}m < MIN_SPAN)",
                        )
                        towers.append(final_tower)
                break
            
            # CRITICAL: Ensure we don't exceed route end
            if next_distance >= route_end_distance:
                # Place final tower at route end (only if span is valid and not duplicate)
                actual_span = route_end_distance - current_distance
                if actual_span >= self.MIN_SPAN and current_distance < route_end_distance:
                    # Check if we already have a tower at this location (strict check)
                    if not towers or (route_end_distance - towers[-1].distance_along_route_m) >= self.MIN_SPAN:
                        final_elevation = self.interpolate_elevation(route_end_distance, terrain_profile)
                        final_lat, final_lon = self._get_coordinates_at_distance(
                            route_end_distance, terrain_profile, route_start_lat, route_start_lon
                        )
                        final_tower = TowerPosition(
                            index=tower_index + 1,
                            distance_along_route_m=route_end_distance,  # CRITICAL FIX 4: Full precision
                            latitude=final_lat,
                            longitude=final_lon,
                            elevation_m=final_elevation,
                            selected_span_m=actual_span,
                            span_selection_reason=f"end-of-line: final span {actual_span:.1f}m",
                        )
                        towers.append(final_tower)
                break
            
            # CRITICAL FIX 1: Ensure span meets minimum requirement
            actual_span_length = next_distance - current_distance
            if actual_span_length < self.MIN_SPAN:
                # Span too short, cannot place tower here
                break
            
            # CRITICAL FIX 1: Prevent duplicate towers (strict check using MIN_SPAN)
            if towers and (next_distance - towers[-1].distance_along_route_m) < self.MIN_SPAN:
                # Next tower would violate minimum span, stop here
                break
            
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
                selected_span_m=selected_span,
                span_selection_reason=reason,
            )
            towers.append(next_tower)
            
            # Move to next tower
            current_distance = next_distance
            tower_index += 1
            
            # Safety check: If we've reached the end, we're done
            if current_distance >= route_end_distance:
                break
        
        # CRITICAL FIX 5: Invariant assertion - validate strict monotonic ordering
        self._validate_tower_sequencing(towers)
        
        return towers
    
    def _validate_tower_sequencing(self, towers: List[TowerPosition]) -> None:
        """
        Validate that towers are in strict monotonic order.
        
        Raises ValueError if any violation is detected.
        """
        if len(towers) < 2:
            return  # No sequencing to validate
        
        for i in range(len(towers) - 1):
            current_x = towers[i].distance_along_route_m
            next_x = towers[i + 1].distance_along_route_m
            span = next_x - current_x
            
            if next_x <= current_x:
                raise ValueError(
                    f"TOWER SEQUENCING VIOLATION: Tower {i} at {current_x:.2f}m must be before "
                    f"Tower {i+1} at {next_x:.2f}m. Towers must be in strict monotonic order."
                )
            
            if span < self.MIN_SPAN:
                raise ValueError(
                    f"MINIMUM SPAN VIOLATION: Span from Tower {i} ({current_x:.2f}m) to "
                    f"Tower {i+1} ({next_x:.2f}m) is {span:.2f}m, which is below minimum "
                    f"required {self.MIN_SPAN:.2f}m."
                )
    
    def _place_towers_simple(
        self,
        terrain_profile: List[TerrainPoint],
        route_start_lat: Optional[float] = None,
        route_start_lon: Optional[float] = None,
    ) -> List[TowerPosition]:
        """
        Simple tower placement (backward compatibility fallback).
        
        Uses fixed max span approach when codal_engine is not available.
        """
        if not terrain_profile:
            return []
        
        towers: List[TowerPosition] = []
        current_distance = 0.0
        tower_index = 0
        route_end_distance = terrain_profile[-1].distance_m if terrain_profile else 0.0
        
        while current_distance < route_end_distance:
            current_elevation = self.interpolate_elevation(current_distance, terrain_profile)
            lat, lon = self._get_coordinates_at_distance(current_distance, terrain_profile, route_start_lat, route_start_lon)
            
            tower = TowerPosition(
                index=tower_index,
                distance_along_route_m=current_distance,
                latitude=lat,
                longitude=lon,
                elevation_m=current_elevation,
            )
            towers.append(tower)
            
            next_distance = current_distance + self.max_span_m
            if next_distance >= route_end_distance:
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
                    selected_span_m=self.max_span_m,
                    span_selection_reason="simple placement (no codal_engine)",
                )
                towers.append(final_tower)
                break
            
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
                # CRITICAL FIX 1: Ensure minimum span from last tower
                if towers and (next_distance - towers[-1].distance_along_route_m) < self.MIN_SPAN:
                    # Cannot place tower here - violates minimum span
                    break
                current_distance = next_distance  # CRITICAL FIX 4: Full precision
                tower_index += 1
            else:
                # CRITICAL FIX 2: Step back collision logic with minimum span enforcement
                candidate_x = next_distance - self.step_back_m
                last_tower_x = tower.distance_along_route_m
                min_required_x = last_tower_x + self.MIN_SPAN
                
                # BEFORE accepting step-back, check monotonic constraint
                if candidate_x <= min_required_x:
                    # Step-back would violate minimum span
                    # Accept previous safe position OR force placement at minimum span
                    if candidate_x < min_required_x:
                        # Force placement at minimum span (if within route bounds)
                        if min_required_x < route_end_distance:
                            current_distance = min_required_x
                            tower_index += 1
                        else:
                            # Cannot place tower - route too short
                            break
                    else:
                        # Exactly at minimum - accept it
                        current_distance = candidate_x
                        tower_index += 1
                else:
                    # Step-back is valid - accept it
                    current_distance = candidate_x
                    tower_index += 1
        
        # CRITICAL FIX 5: Invariant assertion - validate strict monotonic ordering
        self._validate_tower_sequencing(towers)
        
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

