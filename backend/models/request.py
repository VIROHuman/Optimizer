"""
Request models for optimization API.
"""

from pydantic import BaseModel
from typing import Literal, Optional, List, Dict, Any


class OptimizationFlags(BaseModel):
    """Design scenario flags."""
    design_for_higher_wind: bool = False
    include_ice_load: bool = False
    conservative_foundation: bool = False


class OptimizationRequest(BaseModel):
    """Request model for optimization endpoint."""
    location: str
    voltage: int
    terrain: Literal["flat", "rolling", "mountainous", "desert"]
    wind: Literal["zone_1", "zone_2", "zone_3", "zone_4"]
    soil: Literal["soft", "medium", "hard", "rock"]
    tower: Literal["suspension", "angle", "tension", "dead_end"]
    flags: OptimizationFlags
    project_length_km: Optional[float] = None  # Optional project length for line-level estimates
    route_coordinates: Optional[List[Dict[str, Any]]] = None  # Optional route coordinates for map-based placement
    terrain_profile: Optional[List[Dict[str, float]]] = None  # Optional terrain profile: [{ "x": distance_m, "z": elevation_m }]
    row_mode: Literal["government_corridor", "rural_private", "urban_private", "mixed"] = "urban_private"  # ROW scenario

