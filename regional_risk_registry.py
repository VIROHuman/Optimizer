"""
Regional Risk Registry Module.

This module provides contextual awareness of region-specific environmental
and operational risks that may not be covered by the current optimization.

CRITICAL PRINCIPLES:
- INFORMATIONAL ONLY - does NOT affect optimization
- Does NOT reject designs
- Does NOT modify cost calculations
- Makes engineering scope explicit
- Supports informed decision-making

This is a DISCLOSURE LAYER, NOT a design check.
"""

from typing import Dict, List


# Regional risk registry
# Maps regions to known environmental and operational risks
REGIONAL_RISKS: Dict[str, List[str]] = {
    # Europe
    "germany": [
        "Ice accretion / wet snow loading",
        "Frost action in shallow foundations",
        "High construction labor cost",
        "Dense population requiring careful ROW planning",
    ],
    "france": [
        "Ice accretion / wet snow loading",
        "Frost action in shallow foundations",
        "Seismic activity (moderate)",
        "High construction labor cost",
    ],
    "italy": [
        "Seismic activity",
        "Ice accretion in alpine regions",
        "Frost action in shallow foundations",
        "Mountainous terrain access challenges",
    ],
    "spain": [
        "High wind exposure (coastal)",
        "Seismic activity (moderate)",
        "Drought conditions affecting soil",
        "Mountainous terrain access challenges",
    ],
    "uk": [
        "High wind exposure",
        "Ice accretion / wet snow",
        "Frost action in shallow foundations",
        "Dense population requiring careful ROW planning",
    ],
    "united kingdom": [
        "High wind exposure",
        "Ice accretion / wet snow",
        "Frost action in shallow foundations",
        "Dense population requiring careful ROW planning",
    ],
    "netherlands": [
        "Soft alluvial soils",
        "High groundwater levels",
        "Frost action in shallow foundations",
        "Dense population requiring careful ROW planning",
    ],
    "belgium": [
        "Ice accretion / wet snow",
        "Frost action in shallow foundations",
        "Dense population requiring careful ROW planning",
    ],
    "poland": [
        "Ice accretion / wet snow",
        "Frost action in shallow foundations",
        "Extreme cold weather conditions",
    ],
    "europe": [
        "Ice accretion / wet snow loading",
        "Frost action in shallow foundations",
        "High construction labor cost",
        "Dense population requiring careful ROW planning",
    ],
    
    # India
    "india": [
        "Cyclonic winds (coastal regions)",
        "Monsoon flooding",
        "Scour and erosion (river plains)",
        "Soft alluvial soils (Gangetic plains)",
        "High seismic activity (Himalayan foothills)",
        "Corrosion (coastal and industrial areas)",
        "Extreme heat affecting conductor sag",
    ],
    "indian": [
        "Cyclonic winds (coastal regions)",
        "Monsoon flooding",
        "Scour and erosion (river plains)",
        "Soft alluvial soils (Gangetic plains)",
        "High seismic activity (Himalayan foothills)",
        "Corrosion (coastal and industrial areas)",
        "Extreme heat affecting conductor sag",
    ],
    
    # USA / North America
    "usa": [
        "Seismic activity (west coast, midwest)",
        "Wildfire exposure (western states)",
        "Ice accretion (northern states)",
        "Hurricane/cyclonic winds (southeast, gulf coast)",
        "Tornado exposure (midwest, plains)",
        "Extreme cold (northern states)",
        "Expansive soils (southwest)",
    ],
    "united states": [
        "Seismic activity (west coast, midwest)",
        "Wildfire exposure (western states)",
        "Ice accretion (northern states)",
        "Hurricane/cyclonic winds (southeast, gulf coast)",
        "Tornado exposure (midwest, plains)",
        "Extreme cold (northern states)",
        "Expansive soils (southwest)",
    ],
    "canada": [
        "Extreme cold weather conditions",
        "Ice accretion / wet snow",
        "Frost action in shallow foundations",
        "Permafrost (northern regions)",
        "Wildfire exposure (western provinces)",
    ],
    "mexico": [
        "Seismic activity",
        "Hurricane/cyclonic winds (coastal)",
        "Volcanic activity (central regions)",
        "Extreme heat",
    ],
    
    # Middle East
    "uae": [
        "Sandstorms and wind-blown sand",
        "Soil salinity",
        "Extreme heat affecting conductor sag",
        "High construction material import costs",
    ],
    "united arab emirates": [
        "Sandstorms and wind-blown sand",
        "Soil salinity",
        "Extreme heat affecting conductor sag",
        "High construction material import costs",
    ],
    "saudi arabia": [
        "Sandstorms and wind-blown sand",
        "Soil salinity",
        "Extreme heat affecting conductor sag",
        "Desert terrain access challenges",
    ],
    "qatar": [
        "Sandstorms and wind-blown sand",
        "Soil salinity",
        "Extreme heat affecting conductor sag",
        "High groundwater salinity",
    ],
    "kuwait": [
        "Sandstorms and wind-blown sand",
        "Soil salinity",
        "Extreme heat affecting conductor sag",
    ],
    "bahrain": [
        "Sandstorms and wind-blown sand",
        "Soil salinity",
        "Extreme heat affecting conductor sag",
        "High groundwater salinity",
    ],
    "oman": [
        "Sandstorms and wind-blown sand",
        "Cyclonic winds (coastal)",
        "Extreme heat affecting conductor sag",
        "Mountainous terrain access challenges",
    ],
    "middle east": [
        "Sandstorms and wind-blown sand",
        "Soil salinity",
        "Extreme heat affecting conductor sag",
        "High construction material import costs",
    ],
    
    # Africa
    "south africa": [
        "Extreme wind exposure",
        "Remote access logistics",
        "Lightning activity",
        "Bushfire exposure",
        "Corrosion (coastal regions)",
    ],
    "egypt": [
        "Sandstorms and wind-blown sand",
        "Extreme heat affecting conductor sag",
        "Soil salinity",
        "Seismic activity (moderate)",
    ],
    "nigeria": [
        "Monsoon flooding",
        "Corrosion (coastal regions)",
        "Soft alluvial soils",
        "Remote access logistics",
    ],
    "kenya": [
        "High wind exposure",
        "Lightning activity",
        "Remote access logistics",
        "Bushfire exposure",
    ],
    "africa": [
        "Extreme wind exposure",
        "Remote access logistics",
        "Lightning activity",
        "Bushfire exposure",
        "Corrosion (coastal regions)",
    ],
    
    # Australia
    "australia": [
        "Bushfire exposure",
        "Expansive clays",
        "Cyclonic winds (northern regions)",
        "Extreme heat affecting conductor sag",
        "Remote access logistics (outback)",
        "Lightning activity",
        "Corrosion (coastal regions)",
    ],
    "new zealand": [
        "High wind exposure",
        "Seismic activity",
        "Ice accretion (alpine regions)",
        "Corrosion (coastal regions)",
    ],
    "australasia": [
        "Bushfire exposure",
        "Expansive clays",
        "Cyclonic winds (northern regions)",
        "Extreme heat affecting conductor sag",
        "Remote access logistics",
    ],
    
    # Asia-Pacific
    "singapore": [
        "High humidity and corrosion",
        "Dense urban environment",
        "Limited ROW availability",
    ],
    "malaysia": [
        "Monsoon flooding",
        "Cyclonic winds",
        "Corrosion (coastal regions)",
        "High humidity",
    ],
    "thailand": [
        "Monsoon flooding",
        "Cyclonic winds",
        "Corrosion (coastal regions)",
        "High humidity",
    ],
    "indonesia": [
        "Seismic activity",
        "Volcanic activity",
        "Monsoon flooding",
        "Cyclonic winds",
        "Corrosion (coastal regions)",
    ],
    "philippines": [
        "Seismic activity",
        "Volcanic activity",
        "Cyclonic winds (typhoons)",
        "Monsoon flooding",
        "Corrosion (coastal regions)",
    ],
    "vietnam": [
        "Monsoon flooding",
        "Cyclonic winds",
        "Corrosion (coastal regions)",
        "High humidity",
    ],
    
    # South America
    "brazil": [
        "Lightning activity",
        "High humidity and corrosion",
        "Remote access logistics (Amazon)",
        "Flooding (river basins)",
    ],
    "argentina": [
        "High wind exposure (Patagonia)",
        "Seismic activity (western regions)",
        "Extreme cold (southern regions)",
    ],
    "chile": [
        "Seismic activity",
        "Volcanic activity",
        "High wind exposure",
        "Mountainous terrain access challenges",
    ],
}


def get_regional_risks(project_location: str) -> List[str]:
    """
    Get region-specific risks for a project location.
    
    Args:
        project_location: Country or region name (case-insensitive)
        
    Returns:
        List of risk descriptions (empty if region not found)
    """
    location_lower = project_location.lower().strip()
    
    # Direct lookup
    if location_lower in REGIONAL_RISKS:
        return REGIONAL_RISKS[location_lower].copy()
    
    # Partial matching
    for key, risks in REGIONAL_RISKS.items():
        if key in location_lower or location_lower in key:
            return risks.copy()
    
    # Return empty list if no match
    return []


def format_regional_risks(risks: List[str]) -> str:
    """
    Format regional risks for display.
    
    Args:
        risks: List of risk descriptions
        
    Returns:
        Formatted string for display
    """
    if not risks:
        return ""
    
    lines = []
    lines.append("=" * 70)
    lines.append("REGIONAL RISK CONTEXT (INFORMATIONAL)")
    lines.append("=" * 70)
    lines.append("")
    lines.append("Known region-specific risks:")
    lines.append("")
    
    for risk in risks:
        lines.append(f"• {risk}")
    
    lines.append("")
    lines.append("NOTE: These risks are NOT automatically included in the design.")
    lines.append("Additional region-specific risks may require separate evaluation depending on project requirements.")
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)

