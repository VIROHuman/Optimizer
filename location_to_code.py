"""
Location-to-Code Mapping Module.

This module automatically determines the governing design standard
based on the physical project location.

CRITICAL: The optimizer NEVER chooses the standard.
Only ONE design standard applies per optimization run.
"""

from typing import Dict
from data_models import DesignStandard


# Mapping of countries/regions to design standards
LOCATION_TO_STANDARD: Dict[str, DesignStandard] = {
    # India
    "india": DesignStandard.IS,
    "indian": DesignStandard.IS,
    
    # Middle East
    "uae": DesignStandard.IEC,
    "united arab emirates": DesignStandard.IEC,
    "saudi arabia": DesignStandard.IEC,
    "qatar": DesignStandard.IEC,
    "kuwait": DesignStandard.IEC,
    "bahrain": DesignStandard.IEC,
    "oman": DesignStandard.IEC,
    "middle east": DesignStandard.IEC,
    
    # Europe
    "germany": DesignStandard.EUROCODE,
    "france": DesignStandard.EUROCODE,
    "italy": DesignStandard.EUROCODE,
    "spain": DesignStandard.EUROCODE,
    "uk": DesignStandard.EUROCODE,
    "united kingdom": DesignStandard.EUROCODE,
    "netherlands": DesignStandard.EUROCODE,
    "belgium": DesignStandard.EUROCODE,
    "poland": DesignStandard.EUROCODE,
    "europe": DesignStandard.EUROCODE,
    "european union": DesignStandard.EUROCODE,
    "eu": DesignStandard.EUROCODE,
    
    # USA / North America
    "usa": DesignStandard.ASCE,
    "united states": DesignStandard.ASCE,
    "united states of america": DesignStandard.ASCE,
    "canada": DesignStandard.ASCE,
    "mexico": DesignStandard.ASCE,
    "north america": DesignStandard.ASCE,
    
    # Africa (typically IEC/BS)
    "south africa": DesignStandard.IEC,
    "egypt": DesignStandard.IEC,
    "nigeria": DesignStandard.IEC,
    "kenya": DesignStandard.IEC,
    "africa": DesignStandard.IEC,
    
    # Australia / New Zealand
    "australia": DesignStandard.IEC,  # AS/NZS typically aligns with IEC
    "new zealand": DesignStandard.IEC,
    "australasia": DesignStandard.IEC,
    
    # Asia-Pacific (default to IEC)
    "singapore": DesignStandard.IEC,
    "malaysia": DesignStandard.IEC,
    "thailand": DesignStandard.IEC,
    "indonesia": DesignStandard.IEC,
    "philippines": DesignStandard.IEC,
    "vietnam": DesignStandard.IEC,
    
    # South America (default to IEC/ASCE depending on country)
    "brazil": DesignStandard.IEC,
    "argentina": DesignStandard.IEC,
    "chile": DesignStandard.IEC,
}


def get_governing_standard(project_location: str) -> DesignStandard:
    """
    Automatically determine governing design standard from project location.
    
    Args:
        project_location: Country or region name (case-insensitive)
        
    Returns:
        DesignStandard enum value
        
    Raises:
        ValueError: If location is not recognized
        
    Example:
        >>> get_governing_standard("India")
        DesignStandard.IS
        >>> get_governing_standard("UAE")
        DesignStandard.IEC
    """
    location_lower = project_location.lower().strip()
    
    # Direct lookup
    if location_lower in LOCATION_TO_STANDARD:
        return LOCATION_TO_STANDARD[location_lower]
    
    # Partial matching (e.g., "south africa" matches "south africa")
    for key, standard in LOCATION_TO_STANDARD.items():
        if key in location_lower or location_lower in key:
            return standard
    
    # If no match found, raise error
    raise ValueError(
        f"Unknown project location: '{project_location}'. "
        f"Supported locations: {', '.join(sorted(set(LOCATION_TO_STANDARD.values())))}. "
        f"Please specify a recognized country or region."
    )


def get_all_supported_locations() -> Dict[str, DesignStandard]:
    """
    Get all supported location-to-standard mappings.
    
    Returns:
        Dictionary mapping location names to design standards
    """
    return LOCATION_TO_STANDARD.copy()

