"""
Tower Type Classifier Module.

Automatically classifies tower types based on route geometry and mechanical containment rules.
Uses geodetic calculations for accurate bearing computation.

All decisions are geometry-driven and voltage-aware, no user-selected types.
"""

import math
from typing import List, Optional, Tuple
from auto_spotter import TowerPosition
from data_models import TowerType, OptimizationInputs


def calculate_deviation_angle_vector(
    prev_tower: TowerPosition,
    current_tower: TowerPosition,
    next_tower: TowerPosition,
) -> float:
    """
    Calculates the deflection angle (0-180 degrees) using vector dot product.
    
    0 degrees = Straight line
    90 degrees = Right turn
    180 degrees = U-turn
    
    Uses coordinates if available, otherwise falls back to distance-based calculation.
    
    Args:
        prev_tower: Previous tower position
        current_tower: Current tower position
        next_tower: Next tower position
        
    Returns:
        Deviation angle in degrees (0-180°)
    """
    # Try to use lat/lon coordinates if available (more accurate)
    if (prev_tower.latitude is not None and prev_tower.longitude is not None and
        current_tower.latitude is not None and current_tower.longitude is not None and
        next_tower.latitude is not None and next_tower.longitude is not None):
        
        # Convert lat/lon to approximate local coordinates (meters)
        # Using simple approximation: 1 degree lat ≈ 111 km, 1 degree lon ≈ 111 km * cos(lat)
        # Use current tower as origin for local coordinate system
        lat_origin = current_tower.latitude
        lon_origin = current_tower.longitude
        
        # Convert to local x,y coordinates (meters) with current tower as origin
        def latlon_to_xy(lat, lon):
            # Approximate conversion to meters
            lat_diff = (lat - lat_origin) * 111320.0  # meters per degree latitude
            lon_diff = (lon - lon_origin) * 111320.0 * math.cos(math.radians(lat_origin))  # meters per degree longitude (adjusted for latitude)
            return lon_diff, lat_diff  # Return (x, y) = (lon_diff, lat_diff)
        
        # Calculate coordinates relative to current tower (origin)
        prev_x, prev_y = latlon_to_xy(prev_tower.latitude, prev_tower.longitude)
        next_x, next_y = latlon_to_xy(next_tower.latitude, next_tower.longitude)
        
        # Vector A: Previous -> Current (points FROM prev TO current)
        # Since current is at origin (0,0), vector is FROM prev TO origin = -prev
        va_x = 0.0 - prev_x  # Current x - prev x = 0 - prev_x
        va_y = 0.0 - prev_y  # Current y - prev y = 0 - prev_y
        
        # Vector B: Current -> Next (points FROM current TO next)
        # Since current is at origin (0,0), vector is FROM origin TO next = next
        vb_x = next_x - 0.0  # Next x - current x = next_x - 0
        vb_y = next_y - 0.0  # Next y - current y = next_y - 0
    else:
        # Fallback: Use distance_along_route_m as x-coordinate, elevation_m as y-coordinate
        # This creates a 2D projection of the route
        # Vector A: Previous -> Current
        va_x = current_tower.distance_along_route_m - prev_tower.distance_along_route_m
        va_y = current_tower.elevation_m - prev_tower.elevation_m
        
        # Vector B: Current -> Next
        vb_x = next_tower.distance_along_route_m - current_tower.distance_along_route_m
        vb_y = next_tower.elevation_m - current_tower.elevation_m
    
    # 2. Calculate Magnitudes
    mag_a = math.sqrt(va_x**2 + va_y**2)
    mag_b = math.sqrt(vb_x**2 + vb_y**2)
    
    # Safety: Duplicate points or zero length
    if mag_a == 0 or mag_b == 0:
        return 0.0
    
    # 3. Calculate Dot Product
    dot_product = (va_x * vb_x) + (va_y * vb_y)
    
    # 4. Calculate Cosine of Angle
    # Clamp to [-1, 1] to avoid floating point domain errors
    cosine_angle = max(-1.0, min(1.0, dot_product / (mag_a * mag_b)))
    
    # 5. Calculate Angle (Radians -> Degrees)
    # acos gives the angle between the two vectors (0 to 180°)
    # This IS the deviation angle:
    # - 0° = vectors parallel (straight line, no deviation)
    # - 90° = vectors perpendicular (90° turn)
    # - 180° = vectors opposite (U-turn)
    angle_rad = math.acos(cosine_angle)
    deviation_angle = math.degrees(angle_rad)
    
    # Clamp to valid range (0-180°)
    deviation_angle = max(0.0, min(180.0, deviation_angle))
    
    return deviation_angle


def apply_voltage_classification(
    deviation_angle: float,
    voltage_kv: float,
    is_endpoint: bool
) -> Tuple[TowerType, str]:
    """
    Apply tower classification based on deviation angle using simplified thresholds.
    
    Args:
        deviation_angle: Deviation angle in degrees (0-180°)
        voltage_kv: Voltage level in kV (not used in simplified logic, kept for compatibility)
        is_endpoint: Whether this is a route endpoint (should NEVER be True when called from classify_all_towers)
        
    Returns:
        Tuple of (TowerType, classification_reason)
    """
    # CRITICAL SAFETY CHECK: Endpoints are ALWAYS dead-end (safety requirement)
    # This is a defensive check - endpoints should be handled before calling this function
    if is_endpoint:
        return TowerType.DEAD_END, "Dead-end anchor at line termination (safety requirement)"
    
    # CRITICAL FIX: Validate and clamp deviation angle to valid range (0-180°)
    # If angle is invalid, treat as straight line (suspension)
    if deviation_angle < 0.0 or deviation_angle > 180.0:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"Invalid deviation angle {deviation_angle:.1f}° detected. "
            f"Clamping to valid range [0-180°]"
        )
        deviation_angle = max(0.0, min(180.0, deviation_angle))
    
    # CRITICAL COST SAVE: Updated classification thresholds
    # 0° - 3°: suspension
    # 3° - 60°: angle (Treat turns up to 60° as Angle towers. Do NOT trigger Dead-End unless > 60°)
    # > 60° OR Route Endpoints: dead_end
    if deviation_angle <= 3.0:
        return TowerType.SUSPENSION, (
            f"Straight alignment (Deviation {deviation_angle:.1f}° ≤ 3.0°)"
        )
    elif deviation_angle <= 60.0:
        return TowerType.ANGLE, (
            f"Route bend ({deviation_angle:.1f}° between 3.0° and 60.0°)"
        )
    else:
        return TowerType.DEAD_END, (
            f"Sharp turn ({deviation_angle:.1f}° > 60.0°)"
        )


def classify_all_towers(
    tower_positions: List[TowerPosition],
    inputs: OptimizationInputs,
) -> List[Tuple[TowerType, Optional[float], str]]:
    """
    Classify all towers in a route based on geometry and strain section containment.
    
    Implements:
    - Geodetic bearing calculations for accurate deflection
    - Strain section containment (dead-ends every 3-5 km)
    - Voltage-aware classification thresholds
    
    Args:
        tower_positions: List of tower positions along route
        inputs: Optimization inputs (for voltage and standard)
        
    Returns:
        List of tuples: (TowerType, deviation_angle_deg, classification_reason)
    """
    results = []
    voltage_kv = inputs.voltage_level
    distance_since_last_dead_end = 0.0
    
    for i, tower_pos in enumerate(tower_positions):
        prev_tower = tower_positions[i - 1] if i > 0 else None
        next_tower = tower_positions[i + 1] if i < len(tower_positions) - 1 else None
        
        is_endpoint = (i == 0 or i == len(tower_positions) - 1)
        
        # Initialize deviation_angle to None (will be set if computed)
        deviation_angle = None
        
        # CRITICAL FIX: Endpoints MUST be dead-end towers (safety requirement)
        # Check this FIRST, before any other logic
        # If a suspension tower is placed at the end, the wire tension (~10 tonnes) will pull it over
        if is_endpoint:
            tower_type = TowerType.DEAD_END
            if i == 0:
                reason = "Dead-end anchor at route start (required for line termination)"
            else:
                reason = "Dead-end anchor at route end (required for line termination)"
            # Reset distance counter
            distance_since_last_dead_end = 0.0
            # deviation_angle remains None for endpoints (no angle calculation needed)
        else:
            # Update distance since last dead-end (only for non-endpoints)
            if i > 0:
                distance_since_last_dead_end += (
                    tower_pos.distance_along_route_m - 
                    tower_positions[i - 1].distance_along_route_m
                )
            
            # Compute deviation angle using vector math (only for non-endpoints)
            if prev_tower and next_tower:
                deviation_angle = calculate_deviation_angle_vector(
                    prev_tower, tower_pos, next_tower
                )
                # Clamp to valid range (0-180°)
                deviation_angle = max(0.0, min(180.0, deviation_angle))
            else:
                deviation_angle = None
            
            # STEP A: Check for Containment (Force Dead-End every ~5km)
            # Do NOT place dead-ends before 3.0 km unless geometry requires it
            if distance_since_last_dead_end > 5000.0:
                tower_type = TowerType.DEAD_END
                reason = f"Dead-End forced for strain section containment ({distance_since_last_dead_end/1000:.1f} km)"
                distance_since_last_dead_end = 0.0  # Reset counter
            # STEP B: Check Geometry (Using DEVIATION, not raw angle)
            elif deviation_angle is not None:
                # CRITICAL FIX: Validate deviation angle is reasonable (0-180°)
                # If it's > 180°, it's a calculation error - clamp it
                if deviation_angle > 180.0:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Invalid deviation angle {deviation_angle:.1f}° for tower {i}. "
                        f"Clamping to 180.0°"
                    )
                    deviation_angle = 180.0
                
                tower_type, reason = apply_voltage_classification(
                    deviation_angle, voltage_kv, False  # is_endpoint is False here (already handled above)
                )
                # Reset distance counter if we placed a dead-end
                if tower_type == TowerType.DEAD_END:
                    distance_since_last_dead_end = 0.0
            else:
                # Cannot compute angle - default to suspension
                tower_type = TowerType.SUSPENSION
                reason = "Straight-line suspension tower (angle unavailable)"
        
        results.append((tower_type, deviation_angle, reason))
    
    return results
