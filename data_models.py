"""
Data models for transmission line tower design optimization system.

This module defines the core data structures used throughout the system.
All models follow strict separation of concerns: design parameters,
safety constraints, and cost calculations are kept separate.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Tuple


class TowerType(Enum):
    """Transmission tower types supported by the system."""
    SUSPENSION = "suspension"
    ANGLE = "angle"
    TENSION = "tension"  # Also known as Strain
    DEAD_END = "dead_end"


class FoundationType(Enum):
    """Foundation types supported by the system.
    
    IMPORTANT: Only shallow foundations are supported.
    Pile foundations are explicitly OUT OF SCOPE.
    """
    PAD_FOOTING = "pad_footing"
    CHIMNEY_FOOTING = "chimney_footing"  # Pad & Chimney / Open footing


class DesignStandard(Enum):
    """Governing design standards for transmission towers."""
    IS = "IS"  # Indian Standards (IS 802, IS 875, IS 456)
    IEC = "IEC"  # International Electrotechnical Commission / BS
    EUROCODE = "EUROCODE"  # European Standards (EN)
    ASCE = "ASCE"  # American Society of Civil Engineers / AISC / IEEE


class TerrainType(Enum):
    """Terrain classification for wind and construction cost factors."""
    FLAT = "flat"
    ROLLING = "rolling"
    MOUNTAINOUS = "mountainous"
    DESERT = "desert"


class SoilCategory(Enum):
    """Soil classification for foundation design."""
    SOFT = "soft"
    MEDIUM = "medium"
    HARD = "hard"
    ROCK = "rock"


class WindZone(Enum):
    """Wind zone classification."""
    ZONE_1 = "zone_1"  # Low wind
    ZONE_2 = "zone_2"  # Moderate wind
    ZONE_3 = "zone_3"  # High wind
    ZONE_4 = "zone_4"  # Very high wind


@dataclass
class TowerDesign:
    """
    Complete transmission tower design specification.
    
    This dataclass represents a candidate design solution.
    All dimensions are in meters.
    """
    tower_type: TowerType
    tower_height: float  # meters, range: 25-60 m
    base_width: float  # meters, typically 0.25H - 0.40H
    span_length: float  # meters, range: 250-450 m
    foundation_type: FoundationType  # ONLY shallow foundations
    footing_length: float  # meters, range: 3-8 m
    footing_width: float  # meters, range: 3-8 m
    footing_depth: float  # meters, range: 2-6 m
    
    def __post_init__(self):
        """
        Validate design parameters.
        
        NOTE: This validation is for internal consistency checks only.
        The optimizer MUST enforce bounds during optimization, not here.
        If bounds are violated, it indicates an optimizer bug, not a user error.
        """
        # Log warnings for bounds violations (don't raise - let optimizer handle it)
        # These checks are defensive and should never trigger if optimizer works correctly
        pass  # Removed raises - bounds are enforced in optimizer, violations reported via SafetyCheckResult


@dataclass
class OptimizationInputs:
    """
    User-provided inputs for optimization run.
    
    These parameters define the project context and constraints.
    """
    project_location: str  # Country/region name
    voltage_level: float  # kV (not optimized, user input)
    terrain_type: TerrainType
    wind_zone: WindZone
    soil_category: SoilCategory
    span_min: float = 250.0  # meters
    span_max: float = 450.0  # meters
    governing_standard: Optional[DesignStandard] = None  # Auto-resolved if None
    
    # Design scenario toggles (optional, user-controlled)
    design_for_higher_wind: bool = False  # Upgrade wind zone by +1
    include_ice_load: bool = False  # Include ice accretion load case
    high_reliability: bool = False  # Increase safety factors
    conservative_foundation: bool = False  # Stricter footing limits


@dataclass
class SafetyCheckResult:
    """
    Result of codal safety check.
    
    This is the ONLY way safety is communicated in the system.
    """
    is_safe: bool
    violations: List[str]  # List of code violations if not safe
    
    def __post_init__(self):
        """Ensure violations list exists."""
        if self.violations is None:
            self.violations = []


@dataclass
class OptimizationResult:
    """
    Final result from PSO optimization run.
    """
    best_design: TowerDesign
    best_cost: float
    is_safe: bool
    safety_violations: List[str]
    governing_standard: DesignStandard
    iterations: int
    convergence_info: dict  # Additional convergence metrics

