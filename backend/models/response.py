"""
Response models for optimization API.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class DesignResponse(BaseModel):
    """Optimized design parameters."""
    tower_type: str
    tower_height: float
    base_width: float
    span_length: float
    foundation_type: str
    footing_length: float
    footing_width: float
    footing_depth: float


class CostResponse(BaseModel):
    """Cost breakdown."""
    steel_cost: float
    foundation_cost: float
    erection_cost: float
    land_cost: float
    total_cost: float
    currency: str
    currency_symbol: str


class SafetyResponse(BaseModel):
    """Safety status."""
    is_safe: bool
    violations: List[str] = []


class OptimizationResponse(BaseModel):
    """Complete optimization response."""
    design: Dict[str, Any]
    cost: Optional[Dict[str, Any]] = None
    safety: Dict[str, Any]
    warnings: List[Dict[str, Any]] = []  # Changed from List[str] to List[Dict] to preserve warning structure
    advisories: List[Dict[str, Any]] = []
    # Additional fields for complete output mapping
    project_context: Optional[Dict[str, Any]] = None
    line_level_summary: Optional[Dict[str, Any]] = None
    regional_risks: List[Any] = []  # Can be List[str] or List[Dict]
    reference_data_status: Optional[Dict[str, Any]] = None
    design_scenarios_applied: List[str] = []
    optimization_info: Optional[Dict[str, Any]] = None
    codal_engine_name: Optional[str] = None

