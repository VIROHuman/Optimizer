"""
Tower Type Classifier Module.

Automatically classifies tower types based on route geometry.
All decisions are geometry-driven, no hardcoded types.
"""

import math
from typing import List, Optional, Tuple
from auto_spotter import TowerPosition
from data_models import TowerType


def compute_horizontal_deviation_angle(
    prev_tower: Optional[TowerPosition],
    current_tower: TowerPosition,
    next_tower: Optional[TowerPosition],
) -> Optional[float]:
    """
    Compute horizontal deviation angle at current tower location.
    
    Uses three tower coordinates to compute the angle between incoming and outgoing spans.
    
    Args:
        prev_tower: Previous tower position (None for first tower)
        current_tower: Current tower position
        next_tower: Next tower position (None for last tower)
        
    Returns:
        Deviation angle in degrees, or None if cannot be computed
    """
    # Need at least 3 towers to compute angle (prev, current, next)
    if prev_tower is None or next_tower is None:
        return None
    
    # Need coordinates for all three towers
    if (prev_tower.latitude is None or prev_tower.longitude is None or
        current_tower.latitude is None or current_tower.longitude is None or
        next_tower.latitude is None or next_tower.longitude is None):
        return None
    
    # Compute vectors from current tower to previous and next towers
    # Vector 1: current -> previous (incoming span direction, reversed)
    dx1 = prev_tower.longitude - current_tower.longitude
    dy1 = prev_tower.latitude - current_tower.latitude
    
    # Vector 2: current -> next (outgoing span direction)
    dx2 = next_tower.longitude - current_tower.longitude
    dy2 = next_tower.latitude - current_tower.latitude
    
    # Compute angle between vectors using dot product
    # angle = arccos((v1 · v2) / (|v1| * |v2|))
    dot_product = dx1 * dx2 + dy1 * dy2
    magnitude1 = math.sqrt(dx1 * dx1 + dy1 * dy1)
    magnitude2 = math.sqrt(dx2 * dx2 + dy2 * dy2)
    
    # Avoid division by zero
    if magnitude1 == 0.0 or magnitude2 == 0.0:
        return None
    
    # Clamp to [-1, 1] to avoid numerical errors
    cos_angle = max(-1.0, min(1.0, dot_product / (magnitude1 * magnitude2)))
    angle_rad = math.acos(cos_angle)
    angle_deg = math.degrees(angle_rad)
    
    # Compute deviation angle (180° - angle between vectors)
    # This gives the angle the route turns at this tower
    deviation_angle = 180.0 - angle_deg
    
    return deviation_angle


def classify_tower_type(
    tower_index: int,
    total_towers: int,
    deviation_angle_deg: Optional[float],
) -> Tuple[TowerType, str]:
    """
    Classify tower type based on route geometry.
    
    Rules:
    - First and last tower → "dead_end"
    - Angle < 5 degrees → "suspension"
    - Angle between 5 and 30 degrees → "angle"
    - Angle > 30 degrees → "tension"
    
    Args:
        tower_index: Index of current tower (0-based)
        total_towers: Total number of towers
        deviation_angle_deg: Horizontal deviation angle in degrees (None if cannot compute)
        
    Returns:
        Tuple of (TowerType, classification_reason)
    """
    # First and last towers are always dead_end
    if tower_index == 0 or tower_index == total_towers - 1:
        return TowerType.DEAD_END, "First or last tower (dead-end)"
    
    # If angle cannot be computed, default to suspension (most common)
    if deviation_angle_deg is None:
        return TowerType.SUSPENSION, "Angle cannot be computed (default to suspension)"
    
    # Classify based on deviation angle
    abs_angle = abs(deviation_angle_deg)
    
    if abs_angle < 5.0:
        return TowerType.SUSPENSION, f"Deviation angle {abs_angle:.1f}° < 5° (straight line)"
    elif abs_angle < 30.0:
        return TowerType.ANGLE, f"Deviation angle {abs_angle:.1f}° between 5° and 30°"
    else:
        return TowerType.TENSION, f"Deviation angle {abs_angle:.1f}° > 30° (sharp turn)"


def classify_all_towers(
    tower_positions: List[TowerPosition],
) -> List[Tuple[TowerType, Optional[float], str]]:
    """
    Classify all towers in a route based on geometry.
    
    Args:
        tower_positions: List of tower positions along route
        
    Returns:
        List of tuples: (TowerType, deviation_angle_deg, classification_reason)
    """
    results = []
    
    for i, tower_pos in enumerate(tower_positions):
        prev_tower = tower_positions[i - 1] if i > 0 else None
        next_tower = tower_positions[i + 1] if i < len(tower_positions) - 1 else None
        
        # Compute deviation angle
        deviation_angle = compute_horizontal_deviation_angle(
            prev_tower, tower_pos, next_tower
        )
        
        # Classify tower type
        tower_type, reason = classify_tower_type(
            i, len(tower_positions), deviation_angle
        )
        
        results.append((tower_type, deviation_angle, reason))
    
    return results

