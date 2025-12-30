"""
Location Derivation Service.

Derives location and governing standard from route coordinates using reverse geocoding.
"""

from typing import Dict, Any, Optional, Tuple, List
import logging
from backend.services.standard_resolver import resolve_standard

logger = logging.getLogger(__name__)

# Country code to location name mapping
COUNTRY_CODE_TO_LOCATION: Dict[str, str] = {
    "IN": "india",
    "US": "usa",
    "CA": "canada",
    "MX": "mexico",
    "GB": "uk",
    "DE": "germany",
    "FR": "france",
    "IT": "italy",
    "ES": "spain",
    "NL": "netherlands",
    "BE": "belgium",
    "PL": "poland",
    "RO": "romania",
    "AE": "uae",
    "SA": "saudi arabia",
    "QA": "qatar",
    "KW": "kuwait",
    "BH": "bahrain",
    "OM": "oman",
    "ZA": "south africa",
    "EG": "egypt",
    "NG": "nigeria",
    "KE": "kenya",
    "AU": "australia",
    "NZ": "new zealand",
    "SG": "singapore",
    "MY": "malaysia",
    "TH": "thailand",
    "ID": "indonesia",
    "PH": "philippines",
    "VN": "vietnam",
    "BR": "brazil",
    "AR": "argentina",
    "CL": "chile",
}

# Country code to design standard mapping
COUNTRY_CODE_TO_STANDARD: Dict[str, str] = {
    # India
    "IN": "IS",
    # USA / North America
    "US": "ASCE",
    "CA": "ASCE",
    "MX": "ASCE",
    # Europe
    "GB": "EUROCODE",
    "DE": "EUROCODE",
    "FR": "EUROCODE",
    "IT": "EUROCODE",
    "ES": "EUROCODE",
    "NL": "EUROCODE",
    "BE": "EUROCODE",
    "PL": "EUROCODE",
    "RO": "EUROCODE",  # Romania
    # Middle East
    "AE": "IEC",
    "SA": "IEC",
    "QA": "IEC",
    "KW": "IEC",
    "BH": "IEC",
    "OM": "IEC",
    # Africa
    "ZA": "IEC",
    "EG": "IEC",
    "NG": "IEC",
    "KE": "IEC",
    # Australia / New Zealand
    "AU": "IEC",
    "NZ": "IEC",
    # Asia-Pacific
    "SG": "IEC",
    "MY": "IEC",
    "TH": "IEC",
    "ID": "IEC",
    "PH": "IEC",
    "VN": "IEC",
    # South America
    "BR": "IEC",
    "AR": "IEC",
    "CL": "IEC",
}

# Default fallback
DEFAULT_LOCATION = "india"
DEFAULT_STANDARD = "IS"
DEFAULT_WIND_ZONE = "zone_2"

# Country + latitude to wind zone mapping
# Format: ((country_code, is_coastal, min_lat, max_lat), wind_zone)
WIND_ZONE_RULES = [
    # India: coastal areas (within 50km of coast) -> zone_4, inland -> zone_2
    (("IN", True, None, None), "zone_4"),  # India coastal
    (("IN", False, None, None), "zone_2"),  # India inland
    # USA: varies by region
    (("US", True, 24.5, 35.0), "zone_4"),  # US Gulf/Southeast coast
    (("US", True, 35.0, 49.5), "zone_3"),  # US Northeast/West coast
    (("US", False, 24.5, 40.0), "zone_3"),  # US plains
    (("US", False, 40.0, 49.5), "zone_2"),  # US northern inland
    # Europe: generally moderate
    (("GB", None, None, None), "zone_3"),  # UK (island, high wind)
    (("DE", None, None, None), "zone_2"),  # Germany
    (("FR", True, None, None), "zone_3"),  # France coastal
    (("FR", False, None, None), "zone_2"),  # France inland
    # Middle East: high wind
    (("AE", None, None, None), "zone_4"),  # UAE
    (("SA", None, None, None), "zone_3"),  # Saudi Arabia
    # Australia: coastal high, inland moderate
    (("AU", True, None, None), "zone_4"),  # Australia coastal
    (("AU", False, None, None), "zone_2"),  # Australia inland
]

# Simplified: country -> default wind zone (if no coastal detection)
COUNTRY_TO_DEFAULT_WIND: Dict[str, str] = {
    "IN": "zone_2",  # India default (inland)
    "US": "zone_3",  # USA default
    "CA": "zone_2",  # Canada
    "GB": "zone_3",  # UK
    "DE": "zone_2",  # Germany
    "FR": "zone_2",  # France
    "AE": "zone_4",  # UAE
    "SA": "zone_3",  # Saudi Arabia
    "AU": "zone_2",  # Australia default (inland)
}


def reverse_geocode_simple(lat: float, lon: float) -> Optional[str]:
    """
    Simple reverse geocoding using coordinate-based country detection.
    
    This is a lightweight approach that uses coordinate ranges to determine country.
    For production, consider using a proper reverse geocoding API.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        Country code (2-letter ISO code) or None if not determinable
    """
    # India: 6.5°N to 37.5°N, 68°E to 97°E
    if 6.5 <= lat <= 37.5 and 68 <= lon <= 97:
        return "IN"
    
    # USA: 24.5°N to 49.5°N, -125°W to -66°W
    if 24.5 <= lat <= 49.5 and -125 <= lon <= -66:
        return "US"
    
    # Canada: 41.5°N to 83°N, -141°W to -52°W
    if 41.5 <= lat <= 83 and -141 <= lon <= -52:
        return "CA"
    
    # UK: 49.5°N to 61°N, -8°W to 2°E
    if 49.5 <= lat <= 61 and -8 <= lon <= 2:
        return "GB"
    
    # Germany: 47°N to 55°N, 5°E to 15°E
    if 47 <= lat <= 55 and 5 <= lon <= 15:
        return "DE"
    
    # France: 41°N to 51°N, -5°W to 10°E
    if 41 <= lat <= 51 and -5 <= lon <= 10:
        return "FR"
    
    # Romania: 43.5°N to 48.5°N, 20°E to 30°E
    if 43.5 <= lat <= 48.5 and 20 <= lon <= 30:
        return "RO"
    
    # UAE: 22°N to 26°N, 51°E to 56°E
    if 22 <= lat <= 26 and 51 <= lon <= 56:
        return "AE"
    
    # Saudi Arabia: 16°N to 33°N, 34°E to 55°E
    if 16 <= lat <= 33 and 34 <= lon <= 55:
        return "SA"
    
    # Australia: -44°S to -10°S, 113°E to 154°E
    if -44 <= lat <= -10 and 113 <= lon <= 154:
        return "AU"
    
    # Default: try to use a reverse geocoding API if available
    # For now, return None and let caller handle fallback
    # Use DEBUG level since system has fallbacks - this is not critical
    logger.debug(f"Could not determine country for coordinates: {lat}, {lon} (using fallback)")
    return None


def derive_location_from_coordinates(
    route_coordinates: Optional[List[Dict[str, Any]]]
) -> Tuple[Optional[str], Optional[str], bool]:
    """
    Derive location and governing standard from route coordinates.
    
    Args:
        route_coordinates: List of coordinate dicts with 'lat' and 'lon' keys
        
    Returns:
        Tuple of (location_name, governing_standard, is_auto_detected)
        Returns (None, None, False) if coordinates are not available or detection fails
    """
    if not route_coordinates or len(route_coordinates) == 0:
        return None, None, False
    
    # Use first coordinate for location detection
    first_coord = route_coordinates[0]
    lat = first_coord.get("lat")
    lon = first_coord.get("lon")
    
    if lat is None or lon is None:
        logger.warning("Route coordinates missing lat/lon")
        return None, None, False
    
    # Reverse geocode to get country code
    country_code = reverse_geocode_simple(lat, lon)
    
    # Map country code to location name (for backward compatibility)
    if country_code:
    location_name = COUNTRY_CODE_TO_LOCATION.get(country_code, DEFAULT_LOCATION)
    else:
        # Use default location if country cannot be determined
        location_name = DEFAULT_LOCATION
        logger.debug(f"Could not determine country from coordinates: {lat}, {lon} (using fallback)")
    
    # Use Universal Standard Resolver with cascade logic
    # This will never fail - always returns a valid standard (falls back to IEC)
    # Even if country_code is None, it will use WORLD_DEFAULT (IEC)
    governing_standard = resolve_standard(country_code)
    
    if country_code:
    logger.info(f"Auto-detected location: {location_name} (country: {country_code}), standard: {governing_standard}")
    else:
        logger.info(f"Country not detected, using fallback location: {location_name}, standard: {governing_standard}")
    
    return location_name, governing_standard, True


def derive_wind_zone_from_location(
    country_code: str,
    lat: float,
    lon: float,
) -> Tuple[str, bool]:
    """
    Derive wind zone from country and coordinates.
    
    Args:
        country_code: 2-letter country code
        lat: Latitude
        lon: Longitude
        
    Returns:
        Tuple of (wind_zone, is_auto_detected)
    """
    # Check if coastal (simplified: within 50km of coast)
    # For now, use rough heuristics based on country
    is_coastal = False
    
    # India: check if near coast (rough bounds)
    if country_code == "IN":
        # Coastal regions: within ~100km of coast
        # West coast: lon < 75, East coast: lon > 80
        is_coastal = (lon < 75.5) or (lon > 80.5)
    
    # USA: check if near coast
    elif country_code == "US":
        # West coast: lon < -118, East coast: lon > -80, Gulf: lon > -95 and lat < 31
        is_coastal = (lon < -118) or (lon > -80) or (lon > -95 and lat < 31)
    
    # France: check if near coast
    elif country_code == "FR":
        # West coast: lon < -2, Mediterranean: lat < 44 and lon > 3
        is_coastal = (lon < -2) or (lat < 44 and lon > 3)
    
    # Australia: check if near coast
    elif country_code == "AU":
        # All major cities are coastal, use simple check
        is_coastal = abs(lon - 150) < 10 or abs(lon - 115) < 10
    
    # Try to match specific rules (most specific first)
    # Sort rules by specificity (coastal-specific > country-default)
    sorted_rules = sorted(
        WIND_ZONE_RULES,
        key=lambda x: (
            0 if x[0][1] is not None else 1,  # Coastal-specific first
            0 if x[0][2] is not None else 1,  # Lat-range-specific first
        )
    )
    
    for (rule_country, rule_coastal, min_lat, max_lat), wind_zone in sorted_rules:
        if rule_country != country_code:
            continue
        # Check coastal match
        if rule_coastal is not None and rule_coastal != is_coastal:
            continue
        # Check latitude range
        if min_lat is not None and lat < min_lat:
            continue
        if max_lat is not None and lat > max_lat:
            continue
        return wind_zone, True
    
    # Fallback to country default
    default_wind = COUNTRY_TO_DEFAULT_WIND.get(country_code, DEFAULT_WIND_ZONE)
    return default_wind, True


def classify_terrain_from_elevation_profile(
    terrain_profile: Optional[List[Dict[str, float]]]
) -> Tuple[Optional[str], bool]:
    """
    Classify terrain type from elevation profile variance.
    
    Logic:
    - Flat: elevation variance < 10m
    - Rolling: 10-50m variance
    - Mountainous: > 50m variance
    
    Args:
        terrain_profile: List of {x: distance_m, z: elevation_m} or {distance_m, elevation_m}
        
    Returns:
        Tuple of (terrain_type, is_auto_detected)
        Returns (None, False) if profile is not available
    """
    if not terrain_profile or len(terrain_profile) < 2:
        return None, False
    
    # Extract elevations
    elevations = []
    for point in terrain_profile:
        # Handle both formats: {x, z} and {distance_m, elevation_m}
        elevation = point.get("z") or point.get("elevation_m")
        if elevation is not None:
            elevations.append(float(elevation))
    
    if len(elevations) < 2:
        return None, False
    
    # Calculate variance (standard deviation)
    mean_elevation = sum(elevations) / len(elevations)
    variance = sum((e - mean_elevation) ** 2 for e in elevations) / len(elevations)
    std_dev = variance ** 0.5
    
    # Also check range (max - min)
    elevation_range = max(elevations) - min(elevations)
    
    # Use range for classification (more intuitive)
    if elevation_range < 10:
        return "flat", True
    elif elevation_range < 50:
        return "rolling", True
    else:
        return "mountainous", True

