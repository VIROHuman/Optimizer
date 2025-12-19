"""
Cost Context Generator.

Generates plain-language explanations of cost drivers.
Replaces misleading "industry norm deviations".
"""

from typing import List
from backend.models.canonical import CostBreakdownResponse, CostContextResponse


def generate_cost_context(
    cost_breakdown: CostBreakdownResponse,
    cost_per_km: float,
    row_mode: str,
) -> CostContextResponse:
    """
    Generate cost context explanation.
    
    Args:
        cost_breakdown: Cost breakdown totals
        cost_per_km: Cost per kilometer
        row_mode: ROW mode used
        
    Returns:
        CostContextResponse with drivers and interpretation
    """
    # Calculate total from cost breakdown components
    total = (
        cost_breakdown.steel_total +
        cost_breakdown.foundation_total +
        cost_breakdown.erection_total +
        cost_breakdown.transport_total +
        cost_breakdown.land_ROW_total
    )
    if total == 0:
        return CostContextResponse(
            cost_per_km=cost_per_km,
            primary_cost_drivers=["Cost calculation incomplete"],
            interpretation="Cost breakdown unavailable.",
        )
    
    steel_pct = (cost_breakdown.steel_total / total) * 100
    foundation_pct = (cost_breakdown.foundation_total / total) * 100
    erection_pct = (cost_breakdown.erection_total / total) * 100
    transport_pct = (cost_breakdown.transport_total / total) * 100
    row_pct = (cost_breakdown.land_ROW_total / total) * 100
    
    # Identify primary drivers (top 2-3)
    drivers = []
    
    if row_pct >= 50:
        drivers.append(f"Right-of-Way acquisition ({row_pct:.0f}%)")
        if row_mode == "urban_private":
            drivers.append("Conservative urban land compensation model")
            drivers.append("Full private land acquisition assumed")
        elif row_mode == "government_corridor":
            drivers.append("Government corridor easement model")
        elif row_mode == "rural_private":
            drivers.append("Rural private land compensation")
        elif row_mode == "mixed":
            drivers.append("Mixed ROW scenario (urban + rural)")
    elif steel_pct >= 40:
        drivers.append(f"Steel structure ({steel_pct:.0f}%)")
        drivers.append("High voltage requires substantial steel")
    elif foundation_pct >= 30:
        drivers.append(f"Foundation construction ({foundation_pct:.0f}%)")
        drivers.append("Complex soil conditions or conservative design")
    
    if erection_pct >= 20:
        drivers.append(f"Transport & erection ({erection_pct:.0f}%)")
    
    # Generate interpretation
    interpretation_parts = []
    
    if row_pct >= 50:
        interpretation_parts.append(
            "Suitable for early-stage feasibility and worst-case budgeting."
        )
        if row_mode == "urban_private":
            interpretation_parts.append(
                "Not representative of government-corridor or rural projects."
            )
            interpretation_parts.append(
                "Cost expected to reduce significantly with ROW model refinement."
            )
        elif row_mode == "government_corridor":
            interpretation_parts.append(
                "Assumes government-owned corridor with minimal compensation."
            )
    else:
        interpretation_parts.append(
            "Cost structure reflects optimized tower design and construction."
        )
        interpretation_parts.append(
            "ROW component is moderate; primary costs are structural."
        )
    
    interpretation = " ".join(interpretation_parts)
    
    return CostContextResponse(
        cost_per_km=cost_per_km,
        primary_cost_drivers=drivers[:5],  # Top 5 drivers
        interpretation=interpretation,
    )

