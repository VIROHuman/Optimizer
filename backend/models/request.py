"""
Request models for optimization API.
"""

from pydantic import BaseModel
from typing import Literal, Optional, List, Dict, Any
from backend.models.geo_context import GeoContext


class OptimizationFlags(BaseModel):
    """Design scenario flags."""
    design_for_higher_wind: bool = False
    include_ice_load: bool = False
    conservative_foundation: bool = False


class OptimizationRequest(BaseModel):
    """Request model for optimization endpoint."""
    geo_context: Optional[GeoContext] = None  # Geographic context from map reverse geocoding
    voltage: int
    terrain: Optional[Literal["flat", "rolling", "mountainous", "desert"]] = None  # Optional if terrain_profile provided
    wind: Optional[Literal["zone_1", "zone_2", "zone_3", "zone_4"]] = None  # Optional if route_coordinates provided
    soil: Literal["soft", "medium", "hard", "rock"]
    tower: Literal["suspension", "angle", "tension", "dead_end"]
    flags: OptimizationFlags
    project_length_km: Optional[float] = None  # Optional project length for line-level estimates
    route_coordinates: Optional[List[Dict[str, Any]]] = None  # Optional route coordinates for map-based placement
    terrain_profile: Optional[List[Dict[str, float]]] = None  # Optional terrain profile: [{ "x": distance_m, "z": elevation_m }]
    row_mode: Literal["government_corridor", "rural_private", "urban_private", "mixed"] = "urban_private"  # ROW scenario


class FoundationSafetyValidationRequest(BaseModel):
    """Request model for foundation safety validation endpoint."""
    towers: List[Dict[str, Any]]  # List of TowerResponse objects from optimization result
    project_location: str  # Project location for market rates
    voltage: int
    terrain: Literal["flat", "rolling", "mountainous", "desert"]
    wind: Literal["zone_1", "zone_2", "zone_3", "zone_4"]
    soil: Literal["soft", "medium", "hard", "rock"]
    design_for_higher_wind: bool = False
    include_ice_load: bool = False
    include_broken_wire: bool = False
    auto_correct: bool = True  # Auto-correct unsafe foundations

