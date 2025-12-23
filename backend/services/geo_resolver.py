"""
Geographic Resolution Service.

Resolves governing standard, currency, and regional context from geo_context.
Uses explicit country_code mapping - no guessing.
"""

from typing import Dict, Any, Optional, Tuple
from enum import Enum
from backend.models.geo_context import GeoContext
import logging

logger = logging.getLogger(__name__)


class ResolutionMode(str, Enum):
    """Geographic resolution mode."""
    MAP_DERIVED = "map-derived"
    USER_PROVIDED = "user-provided"
    UNRESOLVED = "unresolved"
    GENERIC_PHYSICS_ONLY = "generic-physics-only"


# Explicit country code to design standard mapping
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

# Explicit country code to currency mapping
COUNTRY_CODE_TO_CURRENCY: Dict[str, Dict[str, str]] = {
    "IN": {"code": "INR", "symbol": "₹", "label": "INR"},
    "US": {"code": "USD", "symbol": "$", "label": "USD"},
    "CA": {"code": "USD", "symbol": "$", "label": "USD"},
    "MX": {"code": "USD", "symbol": "$", "label": "USD"},
    "GB": {"code": "USD", "symbol": "$", "label": "USD"},
    "DE": {"code": "USD", "symbol": "$", "label": "USD"},
    "FR": {"code": "USD", "symbol": "$", "label": "USD"},
    "IT": {"code": "USD", "symbol": "$", "label": "USD"},
    "ES": {"code": "USD", "symbol": "$", "label": "USD"},
    "NL": {"code": "USD", "symbol": "$", "label": "USD"},
    "BE": {"code": "USD", "symbol": "$", "label": "USD"},
    "PL": {"code": "USD", "symbol": "$", "label": "USD"},
    "AE": {"code": "USD", "symbol": "$", "label": "USD"},
    "SA": {"code": "USD", "symbol": "$", "label": "USD"},
    "QA": {"code": "USD", "symbol": "$", "label": "USD"},
    "KW": {"code": "USD", "symbol": "$", "label": "USD"},
    "BH": {"code": "USD", "symbol": "$", "label": "USD"},
    "OM": {"code": "USD", "symbol": "$", "label": "USD"},
    "ZA": {"code": "USD", "symbol": "$", "label": "USD"},
    "EG": {"code": "USD", "symbol": "$", "label": "USD"},
    "NG": {"code": "USD", "symbol": "$", "label": "USD"},
    "KE": {"code": "USD", "symbol": "$", "label": "USD"},
    "AU": {"code": "USD", "symbol": "$", "label": "USD"},
    "NZ": {"code": "USD", "symbol": "$", "label": "USD"},
    "SG": {"code": "USD", "symbol": "$", "label": "USD"},
    "MY": {"code": "USD", "symbol": "$", "label": "USD"},
    "TH": {"code": "USD", "symbol": "$", "label": "USD"},
    "ID": {"code": "USD", "symbol": "$", "label": "USD"},
    "PH": {"code": "USD", "symbol": "$", "label": "USD"},
    "VN": {"code": "USD", "symbol": "$", "label": "USD"},
    "BR": {"code": "USD", "symbol": "$", "label": "USD"},
    "AR": {"code": "USD", "symbol": "$", "label": "USD"},
    "CL": {"code": "USD", "symbol": "$", "label": "USD"},
}


def resolve_governing_standard(geo_context: Optional[GeoContext]) -> Tuple[Optional[str], ResolutionMode, str]:
    """
    Resolve governing standard from geo_context.
    
    Args:
        geo_context: Geographic context from map reverse geocoding
        
    Returns:
        Tuple of (standard_code, resolution_mode, explanation)
        - standard_code: "IS", "ASCE", "EUROCODE", "IEC", or None for GENERIC_PHYSICS_ONLY
        - resolution_mode: How resolution was performed
        - explanation: Human-readable explanation
    """
    if not geo_context:
        return None, ResolutionMode.UNRESOLVED, "No geographic context provided. Using generic physics-only mode."
    
    if geo_context.resolution_mode == "unresolved" or not geo_context.country_code:
        return None, ResolutionMode.GENERIC_PHYSICS_ONLY, (
            f"Country could not be resolved from coordinates. "
            f"Using generic physics-only mode (no country-specific standards applied)."
        )
    
    country_code = geo_context.country_code.upper()
    
    if country_code in COUNTRY_CODE_TO_STANDARD:
        standard = COUNTRY_CODE_TO_STANDARD[country_code]
        mode = ResolutionMode.MAP_DERIVED if geo_context.resolution_mode == "map-derived" else ResolutionMode.USER_PROVIDED
        explanation = (
            f"Governing standard '{standard}' determined from country code '{country_code}' "
            f"({geo_context.country_name or 'unknown country'}). "
            f"Resolution mode: {geo_context.resolution_mode}."
        )
        return standard, mode, explanation
    else:
        # Country code not in mapping - use generic physics
        return None, ResolutionMode.GENERIC_PHYSICS_ONLY, (
            f"Country code '{country_code}' ({geo_context.country_name or 'unknown'}) "
            f"is not in the standard mapping. Using generic physics-only mode. "
            f"Explicit country-specific standards not available for this region."
        )


def resolve_currency_from_geo(geo_context: Optional[GeoContext]) -> Tuple[Dict[str, str], ResolutionMode, str]:
    """
    Resolve currency from geo_context.
    
    Args:
        geo_context: Geographic context from map reverse geocoding
        
    Returns:
        Tuple of (currency_dict, resolution_mode, explanation)
        - currency_dict: {"code": "...", "symbol": "...", "label": "..."} or None if unresolved
        - resolution_mode: How resolution was performed
        - explanation: Human-readable explanation
    """
    if not geo_context:
        return None, ResolutionMode.UNRESOLVED, "No geographic context provided. Currency cannot be determined."
    
    if geo_context.resolution_mode == "unresolved" or not geo_context.country_code:
        return None, ResolutionMode.UNRESOLVED, (
            f"Country could not be resolved from coordinates. "
            f"Currency cannot be determined without country information."
        )
    
    country_code = geo_context.country_code.upper()
    
    if country_code in COUNTRY_CODE_TO_CURRENCY:
        currency = COUNTRY_CODE_TO_CURRENCY[country_code]
        mode = ResolutionMode.MAP_DERIVED if geo_context.resolution_mode == "map-derived" else ResolutionMode.USER_PROVIDED
        explanation = (
            f"Currency '{currency['code']}' determined from country code '{country_code}' "
            f"({geo_context.country_name or 'unknown country'}). "
            f"Resolution mode: {geo_context.resolution_mode}."
        )
        return currency, mode, explanation
    else:
        # Country code not in mapping - cannot determine currency
        return None, ResolutionMode.UNRESOLVED, (
            f"Country code '{country_code}' ({geo_context.country_name or 'unknown'}) "
            f"is not in the currency mapping. Currency cannot be determined. "
            f"Explicit currency rules not available for this region."
        )

