"""
Dominant Regional Risk Advisory Module.

This module provides advisories about region-dominant, high-consequence risks
that may govern design but are NOT currently being evaluated.

CRITICAL PRINCIPLES:
- ADVISORY ONLY - does NOT affect optimization
- Does NOT reject designs
- Does NOT auto-enable scenarios
- Makes unmodeled risks explicit
- Guides engineering judgement

This is an ADVISORY SYSTEM, not a design check.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from data_models import OptimizationInputs


@dataclass
class DominantRisk:
    """Represents a dominant regional risk."""
    
    name: str
    category: str  # "environmental", "geotechnical", "climatic", "operational"
    effect: str  # Description of governing load effect
    scenario_toggle: Optional[str]  # Recommended scenario toggle (if available)
    voltage_applicable: Optional[List[float]] = None  # Voltage levels where risk applies (None = all)


@dataclass
class RiskAdvisory:
    """Represents a single risk advisory."""
    
    risk: DominantRisk
    reason: str  # Why it governs in this region
    not_evaluated: str  # What is NOT currently checked
    suggested_action: str  # Suggested scenario toggle or study


# Regional dominant risk registry
REGIONAL_DOMINANT_RISKS: Dict[str, List[DominantRisk]] = {
    # Europe
    "germany": [
        DominantRisk(
            name="Ice accretion / wet snow",
            category="climatic",
            effect="Vertical + combined wind loading on conductors",
            scenario_toggle="--include-ice-load",
            voltage_applicable=[220, 400, 765],  # Higher voltages more affected
        ),
        DominantRisk(
            name="Frost action in shallow foundations",
            category="geotechnical",
            effect="Foundation depth requirements, soil heave",
            scenario_toggle="--conservative-foundation",
        ),
    ],
    "france": [
        DominantRisk(
            name="Ice accretion / wet snow",
            category="climatic",
            effect="Vertical + combined wind loading on conductors",
            scenario_toggle="--include-ice-load",
            voltage_applicable=[220, 400, 765],
        ),
        DominantRisk(
            name="Seismic activity (moderate)",
            category="geotechnical",
            effect="Foundation and structural response",
            scenario_toggle="--high-reliability",
        ),
    ],
    "italy": [
        DominantRisk(
            name="Seismic activity",
            category="geotechnical",
            effect="Foundation and structural response",
            scenario_toggle="--high-reliability",
        ),
        DominantRisk(
            name="Ice accretion (alpine regions)",
            category="climatic",
            effect="Vertical + combined wind loading",
            scenario_toggle="--include-ice-load",
            voltage_applicable=[220, 400],
        ),
    ],
    "spain": [
        DominantRisk(
            name="High wind exposure (coastal)",
            category="climatic",
            effect="Extreme transverse wind loading",
            scenario_toggle="--design-for-higher-wind",
        ),
        DominantRisk(
            name="Seismic activity (moderate)",
            category="geotechnical",
            effect="Foundation and structural response",
            scenario_toggle="--high-reliability",
        ),
    ],
    "uk": [
        DominantRisk(
            name="High wind exposure",
            category="climatic",
            effect="Extreme transverse wind loading",
            scenario_toggle="--design-for-higher-wind",
        ),
        DominantRisk(
            name="Ice accretion / wet snow",
            category="climatic",
            effect="Vertical + combined wind loading",
            scenario_toggle="--include-ice-load",
            voltage_applicable=[220, 400],
        ),
    ],
    "united kingdom": [
        DominantRisk(
            name="High wind exposure",
            category="climatic",
            effect="Extreme transverse wind loading",
            scenario_toggle="--design-for-higher-wind",
        ),
        DominantRisk(
            name="Ice accretion / wet snow",
            category="climatic",
            effect="Vertical + combined wind loading",
            scenario_toggle="--include-ice-load",
            voltage_applicable=[220, 400],
        ),
    ],
    "netherlands": [
        DominantRisk(
            name="Soft alluvial soils",
            category="geotechnical",
            effect="Foundation settlement and stability",
            scenario_toggle="--conservative-foundation",
        ),
        DominantRisk(
            name="High groundwater levels",
            category="geotechnical",
            effect="Foundation construction and stability",
            scenario_toggle="--conservative-foundation",
        ),
    ],
    "europe": [
        DominantRisk(
            name="Ice accretion / wet snow loading",
            category="climatic",
            effect="Vertical + combined wind loading on conductors",
            scenario_toggle="--include-ice-load",
            voltage_applicable=[220, 400, 765],
        ),
        DominantRisk(
            name="Frost action in shallow foundations",
            category="geotechnical",
            effect="Foundation depth requirements",
            scenario_toggle="--conservative-foundation",
        ),
    ],
    
    # India
    "india": [
        DominantRisk(
            name="Cyclonic winds (coastal regions)",
            category="climatic",
            effect="Extreme transverse wind loading",
            scenario_toggle="--design-for-higher-wind",
        ),
        DominantRisk(
            name="Monsoon flooding",
            category="environmental",
            effect="Foundation scour and instability",
            scenario_toggle="--conservative-foundation",
        ),
        DominantRisk(
            name="Scour and erosion (river plains)",
            category="geotechnical",
            effect="Foundation instability",
            scenario_toggle="--conservative-foundation",
        ),
    ],
    "indian": [
        DominantRisk(
            name="Cyclonic winds (coastal regions)",
            category="climatic",
            effect="Extreme transverse wind loading",
            scenario_toggle="--design-for-higher-wind",
        ),
        DominantRisk(
            name="Monsoon flooding",
            category="environmental",
            effect="Foundation scour and instability",
            scenario_toggle="--conservative-foundation",
        ),
    ],
    
    # USA / North America
    "usa": [
        DominantRisk(
            name="Seismic activity (west coast, midwest)",
            category="geotechnical",
            effect="Foundation and structural response",
            scenario_toggle="--high-reliability",
        ),
        DominantRisk(
            name="Wildfire exposure (western states)",
            category="environmental",
            effect="Structural exposure, material degradation",
            scenario_toggle=None,  # No direct toggle, advisory only
        ),
        DominantRisk(
            name="Ice accretion (northern states)",
            category="climatic",
            effect="Vertical + combined wind loading",
            scenario_toggle="--include-ice-load",
            voltage_applicable=[220, 400, 765],
        ),
        DominantRisk(
            name="Hurricane/cyclonic winds (southeast, gulf coast)",
            category="climatic",
            effect="Extreme transverse wind loading",
            scenario_toggle="--design-for-higher-wind",
        ),
        DominantRisk(
            name="Tornado exposure (midwest, plains)",
            category="climatic",
            effect="Extreme wind loading",
            scenario_toggle="--design-for-higher-wind",
        ),
    ],
    "united states": [
        DominantRisk(
            name="Seismic activity (west coast, midwest)",
            category="geotechnical",
            effect="Foundation and structural response",
            scenario_toggle="--high-reliability",
        ),
        DominantRisk(
            name="Wildfire exposure (western states)",
            category="environmental",
            effect="Structural exposure, material degradation",
            scenario_toggle=None,
        ),
    ],
    "canada": [
        DominantRisk(
            name="Extreme cold weather conditions",
            category="climatic",
            effect="Material properties, construction logistics",
            scenario_toggle=None,
        ),
        DominantRisk(
            name="Ice accretion / wet snow",
            category="climatic",
            effect="Vertical + combined wind loading",
            scenario_toggle="--include-ice-load",
            voltage_applicable=[220, 400, 765],
        ),
        DominantRisk(
            name="Permafrost (northern regions)",
            category="geotechnical",
            effect="Foundation design requirements",
            scenario_toggle="--conservative-foundation",
        ),
    ],
    
    # Middle East
    "uae": [
        DominantRisk(
            name="Sandstorms and wind-blown sand",
            category="climatic",
            effect="Material degradation, access issues",
            scenario_toggle=None,
        ),
        DominantRisk(
            name="Extreme heat",
            category="climatic",
            effect="Conductor sag, material properties",
            scenario_toggle=None,
        ),
    ],
    "saudi arabia": [
        DominantRisk(
            name="Sandstorms and wind-blown sand",
            category="climatic",
            effect="Material degradation, access issues",
            scenario_toggle=None,
        ),
        DominantRisk(
            name="Extreme heat",
            category="climatic",
            effect="Conductor sag, material properties",
            scenario_toggle=None,
        ),
    ],
    "middle east": [
        DominantRisk(
            name="Sandstorms and wind-blown sand",
            category="climatic",
            effect="Material degradation, access issues",
            scenario_toggle=None,
        ),
        DominantRisk(
            name="Extreme heat",
            category="climatic",
            effect="Conductor sag, material properties",
            scenario_toggle=None,
        ),
    ],
    
    # Africa
    "south africa": [
        DominantRisk(
            name="Extreme wind exposure",
            category="climatic",
            effect="Extreme transverse wind loading",
            scenario_toggle="--design-for-higher-wind",
        ),
        DominantRisk(
            name="Remote access logistics",
            category="operational",
            effect="Construction risk, cost escalation",
            scenario_toggle=None,
        ),
    ],
    "africa": [
        DominantRisk(
            name="Extreme wind exposure",
            category="climatic",
            effect="Extreme transverse wind loading",
            scenario_toggle="--design-for-higher-wind",
        ),
        DominantRisk(
            name="Remote access logistics",
            category="operational",
            effect="Construction risk, cost escalation",
            scenario_toggle=None,
        ),
    ],
    
    # Australia
    "australia": [
        DominantRisk(
            name="Bushfire exposure",
            category="environmental",
            effect="Structural exposure, material degradation",
            scenario_toggle=None,
        ),
        DominantRisk(
            name="Cyclonic winds (northern regions)",
            category="climatic",
            effect="Extreme transverse wind loading",
            scenario_toggle="--design-for-higher-wind",
        ),
        DominantRisk(
            name="Remote access logistics (outback)",
            category="operational",
            effect="Construction risk, cost escalation",
            scenario_toggle=None,
        ),
    ],
    
    # Asia-Pacific
    "japan": [
        DominantRisk(
            name="Seismic soil liquefaction",
            category="geotechnical",
            effect="Foundation failure under seismic loading",
            scenario_toggle="--conservative-foundation",
        ),
        DominantRisk(
            name="Seismic activity",
            category="geotechnical",
            effect="Foundation and structural response",
            scenario_toggle="--high-reliability",
        ),
    ],
    "philippines": [
        DominantRisk(
            name="Seismic activity",
            category="geotechnical",
            effect="Foundation and structural response",
            scenario_toggle="--high-reliability",
        ),
        DominantRisk(
            name="Cyclonic winds (typhoons)",
            category="climatic",
            effect="Extreme transverse wind loading",
            scenario_toggle="--design-for-higher-wind",
        ),
    ],
    "indonesia": [
        DominantRisk(
            name="Seismic activity",
            category="geotechnical",
            effect="Foundation and structural response",
            scenario_toggle="--high-reliability",
        ),
        DominantRisk(
            name="Volcanic activity",
            category="environmental",
            effect="Ash loading, material degradation",
            scenario_toggle=None,
        ),
    ],
}


def get_dominant_risks(project_location: str) -> List[DominantRisk]:
    """
    Get dominant risks for a project location.
    
    Args:
        project_location: Country or region name (case-insensitive)
        
    Returns:
        List of DominantRisk objects (empty if region not found)
    """
    location_lower = project_location.lower().strip()
    
    # Direct lookup
    if location_lower in REGIONAL_DOMINANT_RISKS:
        return REGIONAL_DOMINANT_RISKS[location_lower].copy()
    
    # Partial matching
    for key, risks in REGIONAL_DOMINANT_RISKS.items():
        if key in location_lower or location_lower in key:
            return risks.copy()
    
    # Return empty list if no match
    return []


def check_scenario_toggle_enabled(
    risk: DominantRisk,
    inputs: OptimizationInputs
) -> bool:
    """
    Check if the recommended scenario toggle for a risk is enabled.
    
    Args:
        risk: DominantRisk to check
        inputs: OptimizationInputs with scenario toggles
        
    Returns:
        True if toggle is enabled, False otherwise
    """
    if risk.scenario_toggle is None:
        return False  # No toggle available
    
    toggle_map = {
        "--include-ice-load": inputs.include_ice_load,
        "--design-for-higher-wind": inputs.design_for_higher_wind,
        "--high-reliability": inputs.high_reliability,
        "--conservative-foundation": inputs.conservative_foundation,
    }
    
    return toggle_map.get(risk.scenario_toggle, False)


def is_risk_applicable(
    risk: DominantRisk,
    voltage_level: float
) -> bool:
    """
    Check if a risk is applicable to the given voltage level.
    
    Args:
        risk: DominantRisk to check
        voltage_level: Voltage level in kV
        
    Returns:
        True if risk applies, False otherwise
    """
    if risk.voltage_applicable is None:
        return True  # Applies to all voltages
    
    return voltage_level in risk.voltage_applicable


def generate_risk_advisories(
    inputs: OptimizationInputs
) -> List[RiskAdvisory]:
    """
    Generate risk advisories for the given project inputs.
    
    Escalates severity for high-voltage lines (≥220 kV) when risk is dominant.
    
    Args:
        inputs: OptimizationInputs with project context
        
    Returns:
        List of RiskAdvisory objects (empty if no advisories needed)
    """
    advisories = []
    
    # Get dominant risks for region
    dominant_risks = get_dominant_risks(inputs.project_location)
    
    # High-voltage threshold for escalation
    high_voltage_threshold = 220.0  # kV
    
    for risk in dominant_risks:
        # Check if risk is applicable to voltage level
        if not is_risk_applicable(risk, inputs.voltage_level):
            continue
        
        # Check if corresponding scenario toggle is enabled
        if check_scenario_toggle_enabled(risk, inputs):
            continue  # Risk is being evaluated, no advisory needed
        
        # Determine if this is a high-voltage, dominant risk
        is_high_voltage = inputs.voltage_level >= high_voltage_threshold
        is_dominant = risk.voltage_applicable is None or inputs.voltage_level in risk.voltage_applicable
        
        # Generate advisory with escalation for high-voltage dominant risks
        if is_high_voltage and is_dominant:
            # Escalated advisory for high-voltage lines
            reason = f"For high-voltage overhead lines in this region, {risk.name.lower()} frequently governs design."
            not_evaluated = f"This scenario is NOT currently evaluated."
            
            if risk.scenario_toggle:
                suggested_action = (
                    f"Strongly consider enabling:\n  {risk.scenario_toggle}\n\n"
                    f"to evaluate {risk.effect.lower()}."
                )
            else:
                suggested_action = (
                    f"Strongly consider additional studies or design measures "
                    f"for {risk.effect.lower()}."
                )
        else:
            # Standard advisory
            reason = f"This region frequently experiences {risk.name.lower()}."
            if risk.category == "climatic":
                reason = f"This region is prone to {risk.name.lower()}."
            elif risk.category == "geotechnical":
                reason = f"This region has significant {risk.name.lower()}."
            elif risk.category == "environmental":
                reason = f"This region faces {risk.name.lower()}."
            
            not_evaluated = f"This design does NOT currently include {risk.name.lower()} evaluation."
            
            if risk.scenario_toggle:
                suggested_action = f"Consider enabling:\n  {risk.scenario_toggle}\n\nto evaluate {risk.effect.lower()}."
            else:
                suggested_action = f"Consider additional studies or design measures for {risk.effect.lower()}."
        
        advisories.append(RiskAdvisory(
            risk=risk,
            reason=reason,
            not_evaluated=not_evaluated,
            suggested_action=suggested_action,
        ))
    
    return advisories


def format_risk_advisories(advisories: List[RiskAdvisory]) -> str:
    """
    Format risk advisories for display.
    
    Args:
        advisories: List of RiskAdvisory objects
        
    Returns:
        Formatted string for display
    """
    if not advisories:
        return ""
    
    lines = []
    lines.append("=" * 70)
    lines.append("DOMINANT REGIONAL RISK ADVISORIES")
    lines.append("=" * 70)
    lines.append("")
    
    for i, advisory in enumerate(advisories, 1):
        # Check if this is an escalated advisory (high-voltage dominant risk)
        is_escalated = "Strongly consider" in advisory.suggested_action or "frequently governs" in advisory.reason
        
        if is_escalated:
            lines.append(f"{i}. {advisory.risk.name.upper()} — OFTEN GOVERNING IN THIS REGION")
        else:
            lines.append(f"{i}. {advisory.risk.name.upper()} RISK (REGION-DOMINANT)")
        lines.append("")
        lines.append(f"   {advisory.reason}")
        if not is_escalated:
            lines.append(f"   {advisory.risk.effect} may govern design.")
        lines.append("")
        lines.append(f"   {advisory.not_evaluated}")
        lines.append("")
        lines.append(f"   {advisory.suggested_action}")
        lines.append("")
    
    lines.append("=" * 70)
    lines.append("")
    lines.append("NOTE: This tool evaluates explicitly selected design scenarios.")
    lines.append("Region-dominant risks may govern final design and")
    lines.append("must be assessed based on project requirements.")
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)

