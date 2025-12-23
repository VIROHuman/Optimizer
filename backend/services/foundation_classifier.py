"""
Foundation Classification Module.

FIX 4: Replaces foundation "design" with classification-based approach.

This module classifies foundations based on:
- Soil category
- Terrain type
- Slope (if available)
- Water proximity (if available)

Returns foundation class, confidence, and cost multiplier.
This is classification, not design.
"""

from typing import Dict, Any, Optional, Tuple
from data_models import OptimizationInputs, SoilCategory, TerrainType


def classify_foundation(
    inputs: OptimizationInputs,
    slope_deg: Optional[float] = None,
    water_proximity_m: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Classify foundation type based on site conditions.
    
    FIX 4: This replaces foundation "design" with classification.
    Foundation costs are indicative and classification-based.
    
    Args:
        inputs: OptimizationInputs with soil and terrain
        slope_deg: Terrain slope in degrees (optional)
        water_proximity_m: Distance to water body in meters (optional)
        
    Returns:
        Dictionary with:
        - foundation_class: str ("Likely Pad Footing" / "Likely Pile" / "Likely Rock Anchor")
        - confidence: str ("Low" / "Medium" / "High")
        - cost_multiplier: float (1.0 - 3.5)
        - reasoning: str (explanation)
    """
    soil = inputs.soil_category
    terrain = inputs.terrain_type
    
    # Base classification logic
    foundation_class = "Likely Pad Footing"  # Default
    confidence = "Medium"
    cost_multiplier = 1.0
    reasoning_parts = []
    
    # Soil-based classification
    if soil == SoilCategory.ROCK:
        foundation_class = "Likely Rock Anchor"
        cost_multiplier = 1.2  # Rock anchors are more expensive
        confidence = "High"
        reasoning_parts.append("Rock soil typically requires rock anchors")
    elif soil == SoilCategory.SOFT:
        # Soft soil may require piles
        if terrain == TerrainType.MOUNTAINOUS:
            foundation_class = "Likely Pile"
            cost_multiplier = 2.5
            confidence = "Medium"
            reasoning_parts.append("Soft soil in mountainous terrain often requires piles")
        else:
            foundation_class = "Likely Pad Footing (may require piles)"
            cost_multiplier = 1.8
            confidence = "Low"
            reasoning_parts.append("Soft soil may require piles depending on load")
    elif soil == SoilCategory.MEDIUM:
        foundation_class = "Likely Pad Footing"
        cost_multiplier = 1.0
        confidence = "Medium"
        reasoning_parts.append("Medium soil typically supports pad footings")
    elif soil == SoilCategory.HARD:
        foundation_class = "Likely Pad Footing"
        cost_multiplier = 0.9  # Slightly cheaper on hard soil
        confidence = "High"
        reasoning_parts.append("Hard soil supports standard pad footings")
    
    # Terrain-based adjustments
    if terrain == TerrainType.MOUNTAINOUS:
        cost_multiplier *= 1.3  # Mountainous terrain increases cost
        if confidence == "High":
            confidence = "Medium"
        reasoning_parts.append("Mountainous terrain increases foundation complexity")
    elif terrain == TerrainType.DESERT:
        cost_multiplier *= 1.1
        reasoning_parts.append("Desert conditions may require special considerations")
    
    # Slope-based adjustments
    if slope_deg is not None and slope_deg > 15:
        cost_multiplier *= 1.4
        if confidence == "High":
            confidence = "Medium"
        reasoning_parts.append(f"Steep slope ({slope_deg:.1f}°) increases foundation requirements")
    
    # Water proximity adjustments
    if water_proximity_m is not None and water_proximity_m < 50:
        cost_multiplier *= 1.3
        if confidence == "High":
            confidence = "Medium"
        reasoning_parts.append(f"Water proximity ({water_proximity_m:.0f}m) may require special foundation design")
    
    # Cap cost multiplier
    cost_multiplier = min(cost_multiplier, 3.5)
    
    reasoning = ". ".join(reasoning_parts) if reasoning_parts else "Standard foundation classification"
    
    return {
        "foundation_class": foundation_class,
        "confidence": confidence,
        "cost_multiplier": round(cost_multiplier, 2),
        "reasoning": reasoning,
    }


def get_foundation_cost_multiplier(
    inputs: OptimizationInputs,
    slope_deg: Optional[float] = None,
    water_proximity_m: Optional[float] = None,
) -> float:
    """
    Get foundation cost multiplier based on classification.
    
    Args:
        inputs: OptimizationInputs
        slope_deg: Optional terrain slope
        water_proximity_m: Optional water proximity
        
    Returns:
        Cost multiplier (1.0 - 3.5)
    """
    classification = classify_foundation(inputs, slope_deg, water_proximity_m)
    return classification["cost_multiplier"]

