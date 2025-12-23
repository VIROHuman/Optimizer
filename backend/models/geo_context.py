"""
Geographic Context Models.

Represents resolved geographic information from map coordinates.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class GeoContext(BaseModel):
    """Geographic context resolved from map coordinates."""
    country_code: Optional[str] = Field(None, description="ISO 3166-1 alpha-2 country code (e.g., 'IN', 'US')")
    country_name: Optional[str] = Field(None, description="Full country name (e.g., 'India', 'United States')")
    state: Optional[str] = Field(None, description="State/province name if available")
    resolution_mode: Literal["map-derived", "user-provided", "unresolved"] = Field(
        "unresolved",
        description="How geographic context was determined"
    )


class GeographicResolutionResponse(BaseModel):
    """Geographic resolution status in canonical output."""
    resolution_mode: Literal["map-derived", "user-provided", "unresolved", "generic-physics-only"] = Field(
        ...,
        description="How geographic context was determined"
    )
    country_code: Optional[str] = Field(None, description="ISO 3166-1 alpha-2 country code")
    country_name: Optional[str] = Field(None, description="Full country name")
    state: Optional[str] = Field(None, description="State/province name if available")
    resolution_explanation: str = Field(..., description="Explanation of how resolution was performed")

