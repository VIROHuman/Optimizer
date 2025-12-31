"""
Canonical OptimizationResult Schema.

This module defines the SINGLE canonical output format used by:
- CLI (main.py)
- FastAPI (api.py)
- Frontend (optimization-results.tsx)

CRITICAL: All interfaces MUST use this exact schema.
No deviations, no shortcuts, no frontend-only calculations.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from backend.models.geo_context import GeographicResolutionResponse


class TowerSafetyStatus(str, Enum):
    """Tower safety status."""
    SAFE = "SAFE"
    GOVERNING = "GOVERNING"  # Safe but at limit (governing load case)


class TowerResponse(BaseModel):
    """Single tower object in towers[] array."""
    index: int = Field(..., description="Tower index along route (0-based)")
    distance_along_route_m: float = Field(..., description="Distance from route start in meters")
    latitude: Optional[float] = Field(None, description="Latitude (if route has coordinates)")
    longitude: Optional[float] = Field(None, description="Longitude (if route has coordinates)")
    tower_type: str = Field(..., description="suspension / tension / angle / dead_end")
    deviation_angle_deg: Optional[float] = Field(None, description="Horizontal deviation angle in degrees (geometry-derived)")
    base_height_m: float = Field(..., description="Base height (ground to first cross-arm)")
    body_extension_m: float = Field(..., description="Body extension height")
    total_height_m: float = Field(..., description="Total tower height")
    base_width_m: float = Field(..., description="Tower base width at ground level (meters)")
    leg_extensions_m: Optional[Dict[str, float]] = Field(None, description="Per-leg extensions if applicable")
    foundation_type: str = Field(..., description="pad_footing / chimney_footing")
    foundation_dimensions: Dict[str, float] = Field(..., description="length, width, depth in meters")
    steel_weight_kg: float = Field(..., description="Steel weight in kg")
    steel_cost: float = Field(..., description="Steel cost")
    foundation_cost: float = Field(..., description="Foundation cost")
    erection_cost: float = Field(..., description="Transport & erection cost")
    transport_cost: float = Field(..., description="Transport cost component")
    land_ROW_cost: float = Field(..., description="Land/ROW cost for this tower")
    total_cost: float = Field(..., description="Total cost for this tower")
    safety_status: TowerSafetyStatus = Field(..., description="SAFE or GOVERNING")
    governing_load_case: Optional[str] = Field(None, description="Governing load case if GOVERNING")
    design_reason: Optional[str] = Field(None, description="Explanation for tower type selection (e.g., 'Angle tower required for 12° route deviation')")
    nudge_description: Optional[str] = Field(None, description="Description of any nudge applied (e.g., 'Shifted 12m fwd to avoid Highway')")
    original_distance_m: Optional[float] = Field(None, description="Original proposed distance before nudge")


class SpanResponse(BaseModel):
    """Single span object in spans[] array."""
    from_tower_index: int = Field(..., description="Index of tower at span start")
    to_tower_index: int = Field(..., description="Index of tower at span end")
    span_length_m: float = Field(..., description="Span length in meters")
    sag_m: float = Field(..., description="Conductor sag at mid-span")
    minimum_clearance_m: float = Field(..., description="Minimum clearance to ground")
    clearance_margin_percent: float = Field(..., description="Clearance margin percentage")
    wind_zone_used: str = Field(..., description="Wind zone applied")
    ice_load_used: bool = Field(..., description="Whether ice load was included")
    governing_case: Optional[str] = Field(None, description="Governing load case")
    is_safe: bool = Field(..., description="Whether span meets clearance requirements")
    confidence_score: Optional[int] = Field(None, description="Confidence score for this span (0-100%)")
    governing_reason: Optional[str] = Field(None, description="Reason why this span is governing")


class LineSummaryResponse(BaseModel):
    """Line-level summary metrics."""
    route_length_km: float = Field(..., description="Total route length in km")
    total_towers: int = Field(..., description="Total number of towers")
    tower_density_per_km: float = Field(..., description="Towers per km (float, 2 decimals)")
    avg_span_m: float = Field(..., description="Average span length in meters")
    tallest_tower_m: float = Field(..., description="Height of tallest tower")
    deepest_foundation_m: float = Field(..., description="Depth of deepest foundation")
    total_steel_tonnes: float = Field(..., description="Total steel weight in tonnes")
    total_concrete_m3: float = Field(..., description="Total concrete volume in m³")
    total_project_cost: float = Field(..., description="Total project cost")
    cost_per_km: float = Field(..., description="Cost per kilometer")
    estimated_towers_for_project_length: Optional[int] = Field(None, description="Estimated towers if project_length_km provided")


class CostBreakdownResponse(BaseModel):
    """Cost breakdown totals."""
    steel_total: float = Field(..., description="Total steel cost")
    foundation_total: float = Field(..., description="Total foundation cost")
    erection_total: float = Field(..., description="Total erection cost")
    transport_total: float = Field(..., description="Total transport cost")
    land_ROW_total: float = Field(..., description="Total land/ROW cost")
    total_project_cost: float = Field(..., description="Total project cost (sum of all components)")
    currency: str = Field(..., description="USD or INR")
    currency_symbol: str = Field(..., description="$ or ₹")
    market_rates: Optional[Dict[str, Any]] = Field(None, description="Market rates used for cost calculation (steel_price_usd, cement_price_usd, labor_factor, logistics_factor, description)")


class SafetySummaryResponse(BaseModel):
    """Safety summary."""
    overall_status: str = Field(..., description="SAFE (always SAFE for final designs)")
    governing_risks: List[str] = Field(default_factory=list, description="List of governing risk factors")
    design_scenarios_applied: List[str] = Field(default_factory=list, description="Design scenarios enabled")


class ConfidenceResponse(BaseModel):
    """Confidence score with drivers."""
    score: int = Field(..., description="Confidence score 0-100%")
    drivers: List[str] = Field(default_factory=list, description="List of factors affecting confidence")


class RegionalContextResponse(BaseModel):
    """Regional context."""
    governing_standard: str = Field(..., description="IS / EN / ASCE / IEC")
    dominant_regional_risks: List[str] = Field(default_factory=list, description="Dominant risks for region")
    confidence: ConfidenceResponse = Field(..., description="Confidence score with drivers")
    wind_source: Optional[str] = Field(None, description="Source of wind zone: 'map-derived' or 'user-selected'")
    terrain_source: Optional[str] = Field(None, description="Source of terrain classification: 'elevation-derived' or 'user-selected'")


class CostSensitivityResponse(BaseModel):
    """Cost sensitivity bands."""
    lower_bound: float = Field(..., description="Lower cost bound")
    upper_bound: float = Field(..., description="Upper cost bound")
    variance_percent: float = Field(..., description="Variance percentage")
    expected_range: str = Field(..., description="Expected range string")


class CostContextResponse(BaseModel):
    """Cost context (indicative) - explains cost drivers."""
    cost_per_km: float = Field(..., description="Cost per kilometer")
    primary_cost_drivers: List[str] = Field(default_factory=list, description="List of primary cost drivers")
    interpretation: str = Field(..., description="Plain-language interpretation of cost")


class CurrencyContextResponse(BaseModel):
    """Currency context for presentation."""
    code: str = Field(..., description="Currency code (USD, INR, etc.)")
    symbol: str = Field(..., description="Currency symbol ($, ₹, etc.)")
    label: str = Field(..., description="Currency label for display")


class CanonicalOptimizationResult(BaseModel):
    """
    Canonical OptimizationResult schema.
    
    This is the SINGLE source of truth for all optimization outputs.
    Used by CLI, API, and Frontend.
    """
    towers: List[TowerResponse] = Field(..., description="MANDATORY: Array of tower objects")
    spans: List[SpanResponse] = Field(..., description="MANDATORY: Array of span objects")
    line_summary: LineSummaryResponse = Field(..., description="MANDATORY: Line-level summary")
    cost_breakdown: CostBreakdownResponse = Field(..., description="MANDATORY: Cost breakdown")
    safety_summary: SafetySummaryResponse = Field(..., description="MANDATORY: Safety summary")
    regional_context: RegionalContextResponse = Field(..., description="MANDATORY: Regional context")
    cost_sensitivity: Optional[CostSensitivityResponse] = Field(None, description="Cost sensitivity bands")
    cost_context: Optional[CostContextResponse] = Field(None, description="Cost context (indicative) - explains cost drivers")
    currency: Optional[CurrencyContextResponse] = Field(None, description="Currency context for presentation (None if unresolved)")
    geographic_resolution: Optional["GeographicResolutionResponse"] = Field(None, description="Geographic resolution status")
    
    # Legacy compatibility fields (deprecated, use canonical fields above)
    warnings: List[Dict[str, Any]] = Field(default_factory=list, description="Constructability warnings")
    advisories: List[Dict[str, Any]] = Field(default_factory=list, description="Risk advisories")
    reference_data_status: Optional[Dict[str, Any]] = Field(None, description="Reference data versions")
    optimization_info: Optional[Dict[str, Any]] = Field(None, description="Optimization metadata")
    obstacles: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Detected obstacles (rivers, highways, steep slopes) for visualization")

