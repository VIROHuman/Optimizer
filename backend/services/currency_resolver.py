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
import logging

logger = logging.getLogger(__name__)


def resolve_currency(
    location: Optional[str] = None,
    route_coordinates: Optional[List[Dict[str, Any]]] = None,
    geo_context: Optional[GeoContext] = None,
    governing_standard: Optional[str] = None
) -> Dict[str, str]:
    """
    Determines currency context for output presentation.
    
    DEPRECATED: Prefer using geo_context with resolve_currency_from_geo().
    
    Args:
        location: Optional location string (deprecated)
        route_coordinates: Optional list of coordinate dicts (deprecated)
        geo_context: Geographic context from map reverse geocoding (preferred)
        governing_standard: Optional governing standard (e.g., "IS" for India)
        
    Returns:
        Dictionary with 'code', 'symbol', 'label', 'resolution_mode', 'resolution_explanation' keys.
        Always returns a valid currency dict (defaults to USD for non-India, INR for India if standard is IS).
        
    Note:
        This is presentation context only, not FX conversion.
        Does not affect optimization math or cost calculations.
    """
    geo_location_error = False
    
    # Prefer geo_context if available
    if geo_context:
        currency_dict, resolution_mode, explanation = resolve_currency_from_geo(geo_context)
        if currency_dict:
            currency_dict["resolution_mode"] = resolution_mode.value
            currency_dict["resolution_explanation"] = explanation
            return currency_dict
        else:
            geo_location_error = True
            logger.warning(
                f"Geolocation derivation error: Currency resolution failed from geo_context. "
                f"Country: {geo_context.country_code if geo_context else 'Unknown'}. "
                f"Falling back to default currency."
            )
    
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
        
        geo_location_error = True
        logger.warning(
            "Geolocation derivation error: Could not determine country from route coordinates. "
            "Falling back to default currency."
        )
    
    # FALLBACK: Default to USD for non-India, INR for India (if standard is IS)
    if governing_standard == "IS":
        # India: Use INR
        return {
            "code": "INR",
            "symbol": "₹",
            "label": "INR",
            "resolution_mode": "fallback-standard",
            "resolution_explanation": "Currency defaulted to INR based on governing standard (IS). "
                                    + ("Geolocation derivation failed." if geo_location_error else "Geographic context unavailable.")
        }
    else:
        # All other countries: Default to USD (International Market Rates)
        logger.info(
            "Currency resolution: Defaulting to USD (International Market Rates). "
            + ("Geolocation derivation failed - could not determine country from coordinates." if geo_location_error else "Geographic context not available.")
        )
        return {
            "code": "USD",
            "symbol": "$",
            "label": "USD",
            "resolution_mode": "fallback-default",
            "resolution_explanation": "Currency defaulted to USD (International Market Rates) for non-India projects. "
                                    + ("Geolocation derivation failed." if geo_location_error else "Geographic context unavailable.")
        }
        return {
            "code": "USD",
            "symbol": "$",
            "label": "USD",
            "resolution_mode": "fallback-default",
            "resolution_explanation": "Currency defaulted to USD (geographic context unavailable or unresolved). "
                                    + ("Geolocation derivation failed." if geo_location_error else "")
        }


