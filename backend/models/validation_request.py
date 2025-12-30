"""
Validation Request Models.

For real-time design validation when towers are moved.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from backend.models.geo_context import GeoContext


class TowerValidationInput(BaseModel):
    """Single tower input for validation."""
    index: int = Field(..., description="Tower index")
    latitude: float = Field(..., description="Tower latitude")
    longitude: float = Field(..., description="Tower longitude")
    total_height_m: float = Field(..., description="Tower height in meters")
    distance_along_route_m: Optional[float] = Field(None, description="Distance along route")


class ValidationRequest(BaseModel):
    """Request for design validation."""
    towers: List[TowerValidationInput] = Field(..., description="List of towers with updated positions")
    spans: List[dict] = Field(..., description="List of spans connecting towers")
    voltage_kv: float = Field(..., description="Line voltage in kV")
    geo_context: Optional[GeoContext] = Field(None, description="Geographic context for standard resolution")
    route_coordinates: Optional[List[dict]] = Field(None, description="Route coordinates for obstacle detection")
    terrain_profile: Optional[List[dict]] = Field(None, description="Terrain elevation profile")


class SpanStatus(BaseModel):
    """Status of a single span validation."""
    span_index: int = Field(..., description="Index of the span")
    from_tower_index: int = Field(..., description="From tower index")
    to_tower_index: int = Field(..., description="To tower index")
    status: str = Field(..., description="Status: 'SAFE' or 'VIOLATION'")
    reason: Optional[str] = Field(None, description="Reason for violation or safety confirmation")
    clearance_m: Optional[float] = Field(None, description="Actual clearance in meters")
    required_clearance_m: Optional[float] = Field(None, description="Required clearance in meters")


class ValidationResponse(BaseModel):
    """Response from design validation."""
    overall_status: str = Field(..., description="Overall status: 'SAFE' or 'VIOLATION'")
    span_statuses: List[SpanStatus] = Field(..., description="Status of each span")
    violations_count: int = Field(..., description="Number of violations found")

