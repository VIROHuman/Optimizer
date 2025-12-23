"""
Span Rebalancing Module.

Rebalances tower positions after auto-spotting to ensure uniform, physically realistic spacing.
"""

import math
from typing import List, Tuple, Optional
from auto_spotter import TowerPosition, TerrainPoint, AutoSpotter
from data_models import OptimizationInputs


def rebalance_spans(
    initial_towers: List[TowerPosition],
    terrain_profile: List[TerrainPoint],
    inputs: OptimizationInputs,
    spotter: AutoSpotter,
    route_start_lat: Optional[float] = None,
    route_start_lon: Optional[float] = None,
) -> Tuple[List[TowerPosition], str, Optional[float]]:
    """
    Rebalance tower positions to ensure uniform span distribution.
    
    Algorithm:
    1. Compute optimal span count based on route length
    2. Compute balanced span length
    3. Rebuild tower positions with uniform spacing
    4. Validate clearance on all rebalanced spans
    5. Fall back to original if clearance violations
    
    Args:
        initial_towers: Initial tower positions from auto-spotter
        terrain_profile: Terrain elevation profile
        inputs: OptimizationInputs with span constraints
        spotter: AutoSpotter instance for clearance checks
        route_start_lat: Optional starting latitude
        route_start_lon: Optional starting longitude
        
    Returns:
        Tuple of (rebalanced_towers, strategy, balanced_span_m)
        strategy: "balanced" if rebalanced, "original" if fallback
        balanced_span_m: Balanced span length if rebalanced, None if fallback
    """
    if len(initial_towers) < 2:
        return initial_towers, "original", None
    
    # Step 1: Compute route parameters
    total_route_length = terrain_profile[-1].distance_m if terrain_profile else 0.0
    if total_route_length <= 0.0:
        return initial_towers, "original", None
    
    max_allowed_span = inputs.span_max
    min_allowed_span = max(inputs.span_min, spotter.MIN_SPAN)  # Use spotter's MIN_SPAN
    
    # Step 2: Compute optimal span count
    # span_count = ceil(total_route_length / max_allowed_span)
    span_count = math.ceil(total_route_length / max_allowed_span)
    
    # Ensure at least 1 span
    if span_count < 1:
        span_count = 1
    
    # Step 3: Compute balanced span length
    # balanced_span = total_route_length / span_count
    balanced_span = total_route_length / span_count
    
    # Step 4: Validate balanced span
    # If balanced_span < MIN_SPAN, reduce span_count until balanced_span >= MIN_SPAN
    while balanced_span < min_allowed_span and span_count > 1:
        span_count -= 1
        balanced_span = total_route_length / span_count
    
    # If balanced_span > MAX_SPAN, increase span_count
    while balanced_span > max_allowed_span:
        span_count += 1
        balanced_span = total_route_length / span_count
    
    # Final validation: ensure balanced span is within bounds
    if balanced_span < min_allowed_span or balanced_span > max_allowed_span:
        # Cannot create balanced spans within constraints
        return initial_towers, "original", None
    
    # Step 5: Rebuild tower positions with uniform spacing
    rebalanced_towers = []
    
    for i in range(span_count + 1):  # +1 because N spans = N+1 towers
        # Compute tower position
        if i == 0:
            # First tower at route start
            tower_x = 0.0
        elif i == span_count:
            # Last tower at route end (exact)
            tower_x = total_route_length
        else:
            # Intermediate towers at uniform spacing
            tower_x = i * balanced_span
        
        # Ensure tower_x doesn't exceed route length (safety check)
        tower_x = min(tower_x, total_route_length)
        
        # Get elevation at this position
        elevation = spotter.interpolate_elevation(tower_x, terrain_profile)
        
        # Get coordinates if available
        lat, lon = spotter._get_coordinates_at_distance(
            tower_x, terrain_profile, route_start_lat, route_start_lon
        )
        
        # Create tower position
        tower = TowerPosition(
            index=i,
            distance_along_route_m=tower_x,  # Full precision, no rounding
            latitude=lat,
            longitude=lon,
            elevation_m=elevation,
            selected_span_m=balanced_span if i > 0 else None,
            span_selection_reason=f"rebalanced: uniform span {balanced_span:.2f}m" if i > 0 else None,
        )
        rebalanced_towers.append(tower)
    
    # Step 6: Re-run terrain clearance + sag checks on rebalanced spans
    clearance_violations = []
    
    for i in range(len(rebalanced_towers) - 1):
        from_tower = rebalanced_towers[i]
        to_tower = rebalanced_towers[i + 1]
        
        # Calculate span length
        span_length = to_tower.distance_along_route_m - from_tower.distance_along_route_m
        
        # Validate span length
        if span_length < min_allowed_span:
            clearance_violations.append(
                f"Span {i} length {span_length:.2f}m < MIN_SPAN {min_allowed_span:.2f}m"
            )
            continue
        
        if span_length > max_allowed_span:
            clearance_violations.append(
                f"Span {i} length {span_length:.2f}m > MAX_SPAN {max_allowed_span:.2f}m"
            )
            continue
        
        # Check clearance using spotter's clearance check
        is_safe, clearance, violation = spotter.check_clearance(
            from_tower, to_tower, terrain_profile
        )
        
        if not is_safe:
            clearance_violations.append(
                f"Span {i} clearance violation: {violation} (clearance: {clearance:.2f}m)"
            )
    
    # Step 7: If ANY span violates clearance, fall back to original
    if clearance_violations:
        return initial_towers, "original", None
    
    # Step 8: Validate strict monotonic ordering
    for i in range(len(rebalanced_towers) - 1):
        if rebalanced_towers[i].distance_along_route_m >= rebalanced_towers[i + 1].distance_along_route_m:
            # Monotonic violation, fall back
            return initial_towers, "original", None
    
    # Rebalancing successful
    return rebalanced_towers, "balanced", balanced_span

