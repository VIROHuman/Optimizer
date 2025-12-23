"""
Currency Resolution Service.

Determines currency context for output presentation based on geo_context.
This is presentation-only logic - no FX conversion or optimization math changes.

DEPRECATED: Use geo_resolver.resolve_currency_from_geo() instead.
This function is kept for backward compatibility.
"""

from typing import Dict, Any, Optional, List
from backend.models.geo_context import GeoContext
from backend.services.geo_resolver import resolve_currency_from_geo


def resolve_currency(
    location: Optional[str] = None,
    route_coordinates: Optional[List[Dict[str, Any]]] = None,
    geo_context: Optional[GeoContext] = None
) -> Optional[Dict[str, str]]:
    """
    Determines currency context for output presentation.
    
    DEPRECATED: Prefer using geo_context with resolve_currency_from_geo().
    
    Args:
        location: Optional location string (deprecated)
        route_coordinates: Optional list of coordinate dicts (deprecated)
        geo_context: Geographic context from map reverse geocoding (preferred)
        
    Returns:
        Dictionary with 'code', 'symbol', 'label', 'resolution_mode', 'resolution_explanation' keys,
        or None if currency cannot be determined
        
    Note:
        This is presentation context only, not FX conversion.
        Does not affect optimization math or cost calculations.
        Returns None if currency cannot be determined (no guessing).
    """
    # Prefer geo_context if available
    if geo_context:
        currency_dict, resolution_mode, explanation = resolve_currency_from_geo(geo_context)
        if currency_dict:
            currency_dict["resolution_mode"] = resolution_mode.value
            currency_dict["resolution_explanation"] = explanation
        return currency_dict
    
    # Legacy fallback: coordinate-based detection (only for India)
    if route_coordinates and len(route_coordinates) > 0:
        # Simple India bounding box (engineering-safe heuristic)
        # India: approximately 6.0°N to 37.5°N, 68.0°E to 97.5°E
        for coord in route_coordinates:
            lat = coord.get("lat")
            lon = coord.get("lon")
            
            if lat is None or lon is None:
                continue
                
            # Check if coordinate is inside India
            if 6.0 <= lat <= 37.5 and 68.0 <= lon <= 97.5:
                return {
                    "code": "INR",
                    "symbol": "₹",
                    "label": "INR",
                    "resolution_mode": "coordinate-based",
                    "resolution_explanation": "Currency determined from coordinate bounding box (India region)."
                }
    
    # Cannot determine currency - return None (no guessing)
    return None


