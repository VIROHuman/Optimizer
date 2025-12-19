"""
Route Optimization Request Models.

New request model for route-level optimization (EPIC 2).
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from backend.models.request import OptimizationFlags


class RouteCoordinate(BaseModel):
    """Single coordinate point along route."""
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    elevation_m: Optional[float] = Field(None, description="Ground elevation in meters")
    distance_m: Optional[float] = Field(None, description="Distance from route start in meters")


class DesignOptions(BaseModel):
    """Design parameters for route optimization."""
    location: str
    voltage: int
    terrain: str  # "flat" | "rolling" | "mountainous" | "desert"
    wind: str  # "zone_1" | "zone_2" | "zone_3" | "zone_4"
    soil: str  # "soft" | "medium" | "hard" | "rock"
    tower: str  # "suspension" | "angle" | "tension" | "dead_end"
    flags: OptimizationFlags


class RouteOptimizationRequest(BaseModel):
    """
    Request model for route-level optimization.
    
    Shifts from single-tower to line-level optimization.
    """
    route_coordinates: List[RouteCoordinate] = Field(
        ...,
        min_items=2,
        description="List of coordinates defining route path. Minimum 2 points required."
    )
    project_length_km: float = Field(
        ...,
        gt=0,
        description="Total project length in kilometers"
    )
    design_options: DesignOptions = Field(
        ...,
        description="Design parameters for optimization"
    )
    row_mode: Literal["government_corridor", "rural_private", "urban_private", "mixed"] = Field(
        "urban_private",
        description="ROW scenario mode"
    )
    
    @validator('route_coordinates')
    def validate_coordinates(cls, v):
        """Validate coordinate shape and consistency."""
        if len(v) < 2:
            raise ValueError("Route must have at least 2 coordinate points")
        
        # Check that all coordinates have lat/lon
        for coord in v:
            if not (-90 <= coord.lat <= 90):
                raise ValueError(f"Invalid latitude: {coord.lat}. Must be between -90 and 90.")
            if not (-180 <= coord.lon <= 180):
                raise ValueError(f"Invalid longitude: {coord.lon}. Must be between -180 and 180.")
        
        return v

