"""
Cost Engine Module.

This module calculates the total cost of a transmission tower design.

CRITICAL PRINCIPLES:
- Computes cost ONLY for safe designs
- Has NO safety logic
- Does NOT validate designs
- Pure cost calculation function
- PER-TOWER cost only (not per-circuit km)

Cost components:
- Steel (tower structure) - regional rates
- Foundation (concrete + excavation) - 4 footings per tower
- Transport & Erection - proportional to steel cost
- Regional adjustment factor

THIS IS A DECISION-SUPPORT COST MODEL, NOT A CONTRACT BOQ.
"""

from typing import Tuple
from data_models import TowerDesign, OptimizationInputs, TerrainType, SoilCategory


# ============================================================================
# REGIONAL STEEL RATES (USD per tonne, fabricated steel)
# ============================================================================

REGIONAL_STEEL_RATES = {
    "india": 1400.0,        # Midpoint of $1,200 - $1,600
    "europe": 2100.0,       # Midpoint of $1,800 - $2,400
    "usa": 2400.0,          # Midpoint of $2,000 - $2,800
    "australia": 2600.0,    # Midpoint of $2,200 - $3,000
    "africa": 1850.0,       # Midpoint of $1,500 - $2,200
    "middle_east": 1950.0,  # Midpoint of $1,600 - $2,300
    "default": 2000.0,      # Default if region not found
}


# ============================================================================
# REGIONAL COST MULTIPLIERS BY CATEGORY
# ============================================================================

# Category-specific regional multipliers
# Replaces single blanket regional factor

REGIONAL_MULTIPLIERS = {
    "india": {
        "steel": 0.90,           # Lower steel cost
        "materials": 0.80,       # Lower concrete/materials cost
        "labor": 0.70,           # Much lower labor cost
        "access": 0.85,          # Lower access/logistics cost
    },
    "europe": {
        "steel": 1.05,           # Slightly higher steel cost
        "materials": 1.10,       # Higher materials cost
        "labor": 1.50,           # Much higher labor cost
        "access": 1.20,          # Higher access/logistics cost
    },
    "usa": {
        "steel": 1.10,           # Higher steel cost
        "materials": 1.15,       # Higher materials cost
        "labor": 1.60,           # Very high labor cost
        "access": 1.25,          # Higher access/logistics cost
    },
    "australia": {
        "steel": 1.15,           # Higher steel cost
        "materials": 1.20,       # Higher materials cost
        "labor": 1.70,           # Very high labor cost
        "access": 1.40,          # High access/logistics (remote)
    },
    "africa": {
        "steel": 0.95,           # Moderate steel cost
        "materials": 0.90,       # Lower materials cost
        "labor": 0.75,           # Lower labor cost
        "access": 1.10,          # Higher access/logistics (remote)
    },
    "middle_east": {
        "steel": 1.00,           # Moderate steel cost
        "materials": 0.95,       # Moderate materials cost
        "labor": 0.85,           # Lower labor cost
        "access": 1.15,          # Higher access/logistics (desert)
    },
    "default": {
        "steel": 1.00,
        "materials": 1.00,
        "labor": 1.00,
        "access": 1.00,
    },
}


# ============================================================================
# REGIONAL LAND / RIGHT-OF-WAY RATES (USD per m²)
# ============================================================================

REGIONAL_LAND_RATES = {
    "india": 50.0,           # USD/m² (rural to urban average)
    "europe": 200.0,        # USD/m² (dense population, high land value)
    "usa": 150.0,           # USD/m² (moderate to high)
    "australia": 80.0,      # USD/m² (mostly rural, some urban)
    "africa": 30.0,         # USD/m² (mostly rural)
    "middle_east": 100.0,   # USD/m² (desert/rural, some urban)
    "default": 100.0,       # Default if region not found
}


# ============================================================================
# ROW MODE CONFIGURATION
# Controls corridor width and compensation multiplier
ROW_MODE_CONFIG = {
    "government_corridor": {"width_m": 35, "multiplier": 0.2},
    "rural_private": {"width_m": 45, "multiplier": 0.6},
    "urban_private": {"width_m": 60, "multiplier": 1.0},
    "mixed": {"width_m": 50, "multiplier": 0.8},
}

# REGIONAL ROW CORRIDOR WIDTHS (meters) - Base widths, modified by row_mode
# ============================================================================

REGIONAL_CORRIDOR_WIDTHS = {
    "india": 50.0,          # m (rural to moderate density)
    "europe": 60.0,         # m (dense population, wider corridor)
    "usa": 55.0,            # m (moderate density)
    "australia": 50.0,      # m (mostly rural)
    "africa": 45.0,         # m (mostly rural, narrower corridor)
    "middle_east": 50.0,    # m (desert/rural)
    "default": 50.0,        # Default if region not found
}


# ============================================================================
# BASE UNIT RATES (region-agnostic)
# ============================================================================

CONCRETE_RATE_PER_M3 = 160.0  # USD/m³ (midpoint of $120 - $200)
EXCAVATION_RATE_PER_M3 = 60.0  # USD/m³ (midpoint of $40 - $80)


# ============================================================================
# SOIL ADJUSTMENT FACTORS (for foundation cost)
# ============================================================================

SOIL_FACTORS = {
    SoilCategory.SOFT: 1.30,
    SoilCategory.MEDIUM: 1.00,
    SoilCategory.HARD: 0.85,
    SoilCategory.ROCK: 0.85,  # Same as hard
}


# ============================================================================
# TERRAIN MULTIPLIERS (for transport & erection)
# ============================================================================

TERRAIN_MULTIPLIERS = {
    TerrainType.FLAT: 1.00,
    TerrainType.ROLLING: 1.15,
    TerrainType.MOUNTAINOUS: 1.30,  # "Hilly" mapped to mountainous
    TerrainType.DESERT: 1.20,
}


def _get_region_from_location(project_location: str) -> str:
    """
    Map project location to cost region.
    
    Args:
        project_location: Country/region name
        
    Returns:
        Region key for cost lookup
    """
    location_lower = project_location.lower().strip()
    
    # India
    if "india" in location_lower or "indian" in location_lower:
        return "india"
    
    # Europe
    europe_keywords = [
        "germany", "france", "italy", "spain", "uk", "united kingdom",
        "netherlands", "belgium", "poland", "europe", "european union", "eu"
    ]
    if any(keyword in location_lower for keyword in europe_keywords):
        return "europe"
    
    # USA / North America
    usa_keywords = [
        "usa", "united states", "united states of america", "canada", "mexico", "north america"
    ]
    if any(keyword in location_lower for keyword in usa_keywords):
        return "usa"
    
    # Australia
    if "australia" in location_lower or "australasia" in location_lower or "new zealand" in location_lower:
        return "australia"
    
    # Middle East
    middle_east_keywords = [
        "uae", "united arab emirates", "saudi arabia", "qatar", "kuwait",
        "bahrain", "oman", "middle east"
    ]
    if any(keyword in location_lower for keyword in middle_east_keywords):
        return "middle_east"
    
    # Africa
    africa_keywords = [
        "south africa", "egypt", "nigeria", "kenya", "africa"
    ]
    if any(keyword in location_lower for keyword in africa_keywords):
        return "africa"
    
    # Default
    return "default"


def calculate_cost(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> float:
    """
    Calculate total cost of a tower design (PER-TOWER).
    
    This function assumes the design is SAFE (has passed codal checks).
    It does NOT perform any safety validation.
    
    Args:
        design: TowerDesign to cost
        inputs: OptimizationInputs containing project context
        
    Returns:
        Total cost in USD (per single tower)
        
    Note:
        This function is deterministic and has no side effects.
        It does NOT modify the design or inputs.
    """
    # Component 1: Steel cost (with regional multiplier)
    steel_cost_base = _calculate_steel_cost(design, inputs)
    region = _get_region_from_location(inputs.project_location)
    steel_multiplier = REGIONAL_MULTIPLIERS.get(region, REGIONAL_MULTIPLIERS["default"])["steel"]
    steel_cost = steel_cost_base * steel_multiplier
    
    # Component 2: Foundation materials cost (with regional multiplier)
    foundation_cost_base = _calculate_foundation_cost(design, inputs)
    materials_multiplier = REGIONAL_MULTIPLIERS.get(region, REGIONAL_MULTIPLIERS["default"])["materials"]
    foundation_cost = foundation_cost_base * materials_multiplier
    
    # Component 3: Transport & Erection cost (with regional multipliers)
    erection_cost_base = _calculate_erection_cost(steel_cost_base, inputs)  # Use base steel cost
    labor_multiplier = REGIONAL_MULTIPLIERS.get(region, REGIONAL_MULTIPLIERS["default"])["labor"]
    access_multiplier = REGIONAL_MULTIPLIERS.get(region, REGIONAL_MULTIPLIERS["default"])["access"]
    # Erection has both labor and access components
    erection_cost = erection_cost_base * labor_multiplier * access_multiplier
    
    # Component 4: Land / Right-of-Way cost
    land_cost = _calculate_land_cost(design, inputs)
    
    # Total per-tower cost (land cost is separate, not multiplied)
    total_cost = steel_cost + foundation_cost + erection_cost + land_cost
    
    return total_cost


def calculate_cost_with_breakdown(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> Tuple[float, dict]:
    """
    Calculate total cost with detailed breakdown.
    
    Args:
        design: TowerDesign to cost
        inputs: OptimizationInputs containing project context
        
    Returns:
        Tuple of (total_cost, breakdown_dict)
        breakdown_dict contains:
        - steel_cost
        - foundation_cost
        - erection_cost
        - regional_factor
        - base_cost (before regional factor)
        - total_cost
        - region
    """
    # Component 1: Steel cost (with regional multiplier)
    steel_cost_base = _calculate_steel_cost(design, inputs)
    region = _get_region_from_location(inputs.project_location)
    steel_multiplier = REGIONAL_MULTIPLIERS.get(region, REGIONAL_MULTIPLIERS["default"])["steel"]
    steel_cost = steel_cost_base * steel_multiplier
    
    # Component 2: Foundation materials cost (with regional multiplier)
    foundation_cost_base = _calculate_foundation_cost(design, inputs)
    materials_multiplier = REGIONAL_MULTIPLIERS.get(region, REGIONAL_MULTIPLIERS["default"])["materials"]
    foundation_cost = foundation_cost_base * materials_multiplier
    
    # Component 3: Transport & Erection cost (with regional multipliers)
    erection_cost_base = _calculate_erection_cost(steel_cost_base, inputs)  # Use base steel cost
    labor_multiplier = REGIONAL_MULTIPLIERS.get(region, REGIONAL_MULTIPLIERS["default"])["labor"]
    access_multiplier = REGIONAL_MULTIPLIERS.get(region, REGIONAL_MULTIPLIERS["default"])["access"]
    erection_cost = erection_cost_base * labor_multiplier * access_multiplier
    
    # Component 4: Land / Right-of-Way cost
    land_cost = _calculate_land_cost(design, inputs)
    
    # Total per-tower cost
    total_cost = steel_cost + foundation_cost + erection_cost + land_cost
    
    breakdown = {
        "steel_cost": steel_cost,
        "foundation_cost": foundation_cost,
        "erection_cost": erection_cost,
        "land_cost": land_cost,
        "total_cost": total_cost,
        "region": region,
        "multipliers": {
            "steel": steel_multiplier,
            "materials": materials_multiplier,
            "labor": labor_multiplier,
            "access": access_multiplier,
        },
    }
    
    return total_cost, breakdown


def _calculate_steel_cost(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> float:
    """
    Calculate steel cost for tower structure.
    
    Uses lattice tower approximation:
    steel_weight_tonnes = k × tower_height × base_width
    
    Where k = 0.10 (default lattice factor)
    
    Args:
        design: TowerDesign
        inputs: OptimizationInputs
        
    Returns:
        Steel cost in USD
    """
    # Lattice factor (empirical, range 0.08 - 0.12)
    k = 0.10
    
    # Tower type multiplier
    type_multiplier = {
        "suspension": 1.0,
        "angle": 1.1,
        "tension": 1.2,
        "dead_end": 1.3,
    }
    multiplier = type_multiplier.get(design.tower_type.value, 1.0)
    
    # Base steel weight in tonnes
    steel_weight_tonnes = k * design.tower_height * design.base_width * multiplier
    
    # Ice load coupling: When ice load is enabled, increase steel demand
    # Ice loading increases vertical forces, requiring stronger cross-arms and members
    if inputs.include_ice_load:
        # Conservative multiplier: ice increases vertical load by ~30-50%
        # This propagates into cross-arm demand, vertical reactions, and member forces
        ice_multiplier = 1.35  # 35% increase in steel weight for ice loading
        steel_weight_tonnes *= ice_multiplier
    
    # Regional steel rate
    region = _get_region_from_location(inputs.project_location)
    steel_rate = REGIONAL_STEEL_RATES.get(region, REGIONAL_STEEL_RATES["default"])
    
    # Cost
    return steel_weight_tonnes * steel_rate


def _calculate_foundation_cost(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> float:
    """
    Calculate foundation cost (concrete + excavation).
    
    Tower has 4 individual leg footings.
    
    Args:
        design: TowerDesign
        inputs: OptimizationInputs
        
    Returns:
        Foundation cost in USD
    """
    # Single footing volume
    single_footing_volume = (
        design.footing_length *
        design.footing_width *
        design.footing_depth
    )
    
    # Total concrete volume (4 footings)
    total_concrete_volume = 4.0 * single_footing_volume
    
    # Concrete cost
    concrete_cost = total_concrete_volume * CONCRETE_RATE_PER_M3
    
    # Excavation volume (foundation + over-excavation)
    foundation_area = design.footing_length * design.footing_width
    over_excavation_factor = 1.2  # 20% over-excavation
    excavation_volume_per_footing = foundation_area * design.footing_depth * over_excavation_factor
    total_excavation_volume = 4.0 * excavation_volume_per_footing
    
    # Excavation cost
    excavation_cost = total_excavation_volume * EXCAVATION_RATE_PER_M3
    
    # Soil adjustment factor
    soil_factor = SOIL_FACTORS.get(inputs.soil_category, SOIL_FACTORS[SoilCategory.MEDIUM])
    
    # Total foundation cost
    base_foundation_cost = concrete_cost + excavation_cost
    foundation_cost = base_foundation_cost * soil_factor
    
    return foundation_cost


def _calculate_erection_cost(
    steel_cost: float,
    inputs: OptimizationInputs
) -> float:
    """
    Calculate transport & erection cost.
    
    Transport & erection cost = 0.25 × steel_cost
    
    Adjusted by terrain difficulty.
    
    Args:
        steel_cost: Steel cost in USD
        inputs: OptimizationInputs
        
    Returns:
        Erection cost in USD
    """
    # Base erection cost (25% of steel cost)
    base_erection_cost = 0.25 * steel_cost
    
    # Terrain multiplier
    terrain_multiplier = TERRAIN_MULTIPLIERS.get(
        inputs.terrain_type,
        TERRAIN_MULTIPLIERS[TerrainType.FLAT]
    )
    
    # Total erection cost
    return base_erection_cost * terrain_multiplier


def _calculate_land_cost(
    design: TowerDesign,
    inputs: OptimizationInputs
) -> float:
    """
    Calculate tower footprint land / right-of-way cost per tower.
    
    This is the SECONDARY ROW component (tower footprint only).
    Corridor ROW cost is calculated separately at line level.
    
    Land footprint is approximated as base_width².
    
    Args:
        design: TowerDesign to cost
        inputs: OptimizationInputs with project location
        
    Returns:
        Tower footprint land cost per tower in USD
    """
    # Approximate tower land footprint (square base)
    footprint_area = design.base_width ** 2  # m²
    
    # Regional land rate
    region = _get_region_from_location(inputs.project_location)
    land_rate = REGIONAL_LAND_RATES.get(region, REGIONAL_LAND_RATES["default"])
    
    # Tower footprint land cost per tower
    land_cost = footprint_area * land_rate
    
    return land_cost


def calculate_row_corridor_cost_per_km(
    inputs: OptimizationInputs,
    row_mode: str = "urban_private"
) -> float:
    """
    Calculate ROW corridor cost per kilometer.
    
    This is the DOMINANT ROW component representing:
    - Compensation under conductors
    - Land devaluation
    - Easements
    - Agricultural loss
    
    Formula:
      ROW_corridor_cost_per_km = corridor_width × land_rate × multiplier × 1000
    
    Args:
        inputs: OptimizationInputs with project location
        row_mode: ROW mode ("government_corridor", "rural_private", "urban_private", "mixed")
        
    Returns:
        ROW corridor cost per kilometer in USD/km
    """
    region = _get_region_from_location(inputs.project_location)
    base_corridor_width = REGIONAL_CORRIDOR_WIDTHS.get(region, REGIONAL_CORRIDOR_WIDTHS["default"])
    land_rate = REGIONAL_LAND_RATES.get(region, REGIONAL_LAND_RATES["default"])
    
    # Apply row_mode configuration
    row_config = ROW_MODE_CONFIG.get(row_mode, ROW_MODE_CONFIG["urban_private"])
    corridor_width = row_config["width_m"]
    multiplier = row_config["multiplier"]
    
    # ROW corridor cost per kilometer
    row_corridor_cost_per_km = corridor_width * land_rate * multiplier * 1000.0
    
    return row_corridor_cost_per_km


def check_cost_sanity(
    total_cost: float,
    voltage_level: float,
    tower_type: str
) -> Tuple[bool, str]:
    """
    Check if cost is within expected range for 400 kV suspension towers.
    
    Args:
        total_cost: Total cost in USD
        voltage_level: Voltage level in kV
        tower_type: Tower type string
        
    Returns:
        Tuple of (is_reasonable, warning_message)
    """
    # Check for 400 kV suspension towers
    if abs(voltage_level - 400.0) < 1.0 and tower_type == "suspension":
        if total_cost > 2000000.0:
            warning = (
                f"WARNING: Cost (${total_cost:,.2f} USD) exceeds typical "
                f"per-tower range for 400 kV suspension towers "
                f"($300,000 - $1,200,000 USD). Check inputs or geometry."
            )
            return False, warning
    
    return True, ""
