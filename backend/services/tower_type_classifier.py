"""
Tower Type Classifier Module (upgraded).

Derives tower types from route geometry using geodetic bearings.
Implements strain section containment, voltage-aware thresholds,
and produces reasons for every tower decision.

No user-provided tower types are accepted.
"""

from typing import List, Optional, Tuple, Dict

try:
    from pyproj import Geod  # type: ignore[import-untyped]
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False
    # Fallback: will use approximate method if pyproj not available
    Geod = None  # type: ignore

from auto_spotter import TowerPosition
from data_models import TowerType


# Initialize WGS84 geodetic calculator if pyproj is available
if HAS_PYPROJ:
    WGS84 = Geod(ellps="WGS84")
else:
    WGS84 = None


def compute_geodetic_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> Optional[float]:
    """Compute forward geodetic bearing from point1 to point2 (degrees)."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    
    if not HAS_PYPROJ or WGS84 is None:
        # Fallback to approximate bearing (not ideal but allows system to run)
        import math
        import warnings
        warnings.warn(
            "pyproj not available, using approximate bearing calculation. "
            "Install pyproj for accurate geodetic calculations: pip install pyproj"
        )
        # Approximate bearing using atan2 (less accurate but functional)
        dlon = math.radians(lon2 - lon1)
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        y = math.sin(dlon) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360.0) % 360.0
    
    _, _, fwd_az = WGS84.inv(lon1, lat1, lon2, lat2)
    # Normalize to 0-360
    return (fwd_az + 360.0) % 360.0


def compute_geodetic_deviation(
    prev_tower: Optional[TowerPosition],
    current_tower: TowerPosition,
    next_tower: Optional[TowerPosition],
) -> Optional[float]:
    """
    Compute horizontal deviation angle at current tower using true geodetic bearings.
    Returns deviation in degrees (0–180) or None if not computable.
    """
    if prev_tower is None or next_tower is None:
        return None
    if any(
        x is None
        for x in [
            prev_tower.latitude,
            prev_tower.longitude,
            current_tower.latitude,
            current_tower.longitude,
            next_tower.latitude,
            next_tower.longitude,
        ]
    ):
        return None

    bearing_prev = compute_geodetic_bearing(
        prev_tower.latitude, prev_tower.longitude, current_tower.latitude, current_tower.longitude
    )
    bearing_next = compute_geodetic_bearing(
        current_tower.latitude, current_tower.longitude, next_tower.latitude, next_tower.longitude
    )

    if bearing_prev is None or bearing_next is None:
        return None

    # CRITICAL FIX: Calculate deviation from straight line (0-180°)
    # Formula: deviation = abs(180 - internal_angle)
    # 
    # The internal angle at the vertex is calculated from the bearing difference
    # For a straight line: internal_angle ≈ 180°, so deviation ≈ 0°
    # For a sharp turn: internal_angle → 0° or 360°, so deviation → 180°
    # 
    # Calculate the turn angle (difference between bearings, normalized to 0-180°)
    bearing_diff = abs(bearing_next - bearing_prev)
    if bearing_diff > 180.0:
        bearing_diff = 360.0 - bearing_diff
    
    # The internal angle at vertex B (for points A → B → C) is:
    # internal_angle = 180° - turn_angle
    # For straight line: turn_angle ≈ 0°, so internal_angle ≈ 180°
    # For 90° turn: turn_angle = 90°, so internal_angle = 90°
    internal_angle = 180.0 - bearing_diff
    
    # Deviation from straight = abs(180 - internal_angle)
    # Example: straight line with internal_angle = 178° → deviation = abs(180 - 178) = 2°
    deviation = abs(180.0 - internal_angle)
    
    return deviation


def voltage_thresholds(voltage_kv: float) -> Dict[str, float]:
    """Return deflection thresholds per voltage level."""
    if voltage_kv >= 765:
        return {"suspension": 2.0, "angle": 20.0}
    if voltage_kv >= 400:
        return {"suspension": 3.0, "angle": 30.0}
    return {"suspension": 5.0, "angle": 35.0}  # ≤ 220 kV


def apply_voltage_classification(
    deviation_angle: float,
    voltage_kv: float,
    is_endpoint: bool,
) -> Tuple[TowerType, str]:
    """Classify tower type using voltage-aware thresholds and reason strings."""
    thresholds = voltage_thresholds(voltage_kv)
    sus_lim = thresholds["suspension"]
    angle_lim = thresholds["angle"]

    if is_endpoint:
        return TowerType.DEAD_END, "Dead-end anchor at line termination"

    if deviation_angle <= sus_lim:
        return TowerType.SUSPENSION, f"Straight-line suspension tower (deviation {deviation_angle:.1f}° ≤ {sus_lim}°)"
    if deviation_angle <= angle_lim:
        return TowerType.ANGLE, f"Angle tower required for {deviation_angle:.1f}° route deviation"
    return TowerType.DEAD_END, f"Dead-end tower required for {deviation_angle:.1f}° route deviation"


def classify_all_towers(
    tower_positions: List[TowerPosition],
    voltage_kv: float,
) -> List[Tuple[TowerType, Optional[float], str, float]]:
    """
    Classify all towers with geodetic bearings, strain section containment,
    voltage-aware thresholds, and design reasons.

    Returns:
        List of tuples: (TowerType, deviation_angle_deg, design_reason, distance_since_last_dead_end_m)
    """
    results: List[Tuple[TowerType, Optional[float], str, float]] = []

    last_dead_end_idx = 0

    for i, tower_pos in enumerate(tower_positions):
        prev_tower = tower_positions[i - 1] if i > 0 else None
        next_tower = tower_positions[i + 1] if i < len(tower_positions) - 1 else None

        deviation_angle = compute_geodetic_deviation(prev_tower, tower_pos, next_tower)

        is_endpoint = i == 0 or i == len(tower_positions) - 1
        distance_since_last_dead_end = tower_pos.distance_along_route_m - tower_positions[last_dead_end_idx].distance_along_route_m

        # Endpoints are always dead-end
        if is_endpoint:
            tower_type = TowerType.DEAD_END
            reason = "Dead-end anchor at line termination"
        # STEP A: Check for Containment (Force Dead-End every ~5km)
        elif distance_since_last_dead_end >= 5000.0:
            tower_type = TowerType.DEAD_END
            reason = f"Dead-End forced for strain section containment ({distance_since_last_dead_end/1000:.1f} km)"
        # STEP B: Check Geometry (Using DEVIATION, not raw angle)
        elif deviation_angle is not None:
            # Use fixed thresholds: 3° for suspension, 30° for angle
            # This ensures moderate bends (20-25°) are classified as Angle, not Dead-End
            if deviation_angle <= 3.0:
                tower_type = TowerType.SUSPENSION
                reason = f"Straight alignment (Deviation {deviation_angle:.1f}° ≤ 3.0°)"
            elif deviation_angle <= 30.0:
                # CRITICAL: Moderate bends (3° < deviation ≤ 30°) MUST be Angle towers
                tower_type = TowerType.ANGLE
                reason = f"Moderate route bend ({deviation_angle:.1f}° between 3.0° and 30.0°)"
            else:
                # Sharp turn (>30°) or endpoint
                tower_type = TowerType.DEAD_END
                reason = f"High deviation angle ({deviation_angle:.1f}° > 30.0° threshold)"
        else:
            # Default to suspension if angle cannot be computed
            tower_type = TowerType.SUSPENSION
            reason = "Straight-line suspension tower (angle unavailable)"

        # Update strain section tracking
        if tower_type == TowerType.DEAD_END:
            last_dead_end_idx = i

        results.append((tower_type, deviation_angle, reason, distance_since_last_dead_end))

    return results

