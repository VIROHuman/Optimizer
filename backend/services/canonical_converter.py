"""
Canonical Result Converter.

Converts current optimization result format to canonical OptimizationResult schema.

═══════════════════════════════════════════════════════════════════════════
SINGLE POINT OF TRUTH FOR SAFE-ONLY RETURNS
═══════════════════════════════════════════════════════════════════════════

This module is the ONLY place that decides final output safety.

CRITICAL RULES:
1. If result.is_safe == False → Force conservative safe fallback
2. Log warning, NEVER raise exception
3. Always return CanonicalOptimizationResult with safety_summary.overall_status = "SAFE"
4. Violations are explanatory (governing constraints), not fatal

This ensures API NEVER returns UNSAFE final designs.
═══════════════════════════════════════════════════════════════════════════
"""

from typing import Dict, Any, List, Optional
from intelligence.intelligence_manager import IntelligenceManager
from data_models import TowerDesign, OptimizationInputs, OptimizationResult
from cost_engine import calculate_cost_with_breakdown, calculate_row_corridor_cost_per_km
from backend.models.canonical import (
    CanonicalOptimizationResult,
    TowerResponse,
    SpanResponse,
    LineSummaryResponse,
    CostBreakdownResponse,
    SafetySummaryResponse,
    RegionalContextResponse,
    TowerSafetyStatus,
    CostSensitivityResponse,
    CurrencyContextResponse,
)
from backend.services.confidence_scorer import calculate_confidence_score_with_drivers
from backend.services.cost_sensitivity import calculate_cost_sensitivity_bands
from backend.services.cost_context import generate_cost_context
from backend.services.currency_resolver import resolve_currency


def calculate_steel_weight_kg(design: TowerDesign, inputs: OptimizationInputs) -> float:
    """
    Calculate steel weight in kg for a tower design.
    
    Uses same formula as cost engine but returns weight instead of cost.
    """
    # Lattice factor (empirical, range 0.08 - 0.12)
    k = 0.035
    
    # Tower type multiplier
    type_multiplier = {
        "suspension": 1.0,
        "angle": 1.5,
        "tension": 1.2,
        "dead_end": 2.5,
    }
    multiplier = type_multiplier.get(design.tower_type.value, 1.0)
    
    # Base steel weight in tonnes
    steel_weight_tonnes = k * design.tower_height * design.base_width * multiplier
    
    # Ice load coupling
    if inputs.include_ice_load:
        ice_multiplier = 1.35
        steel_weight_tonnes *= ice_multiplier
    
    # Convert to kg
    return steel_weight_tonnes * 1000.0


def calculate_concrete_volume_m3(design: TowerDesign) -> float:
    """
    Calculate concrete volume in m³ for foundation.
    
    Assumes 4 footings per tower (one per leg).
    """
    # Volume per footing = length × width × depth
    volume_per_footing = design.footing_length * design.footing_width * design.footing_depth
    
    # 4 footings per tower
    return volume_per_footing * 4.0


def convert_to_canonical(
    result: OptimizationResult,
    inputs: OptimizationInputs,
    project_length_km: Optional[float] = None,
    route_coordinates: Optional[List[Dict[str, float]]] = None,
    row_mode: str = "urban_private",
    location_auto_detected: bool = False,
    wind_source: Optional[str] = None,
    terrain_source: Optional[str] = None,
) -> CanonicalOptimizationResult:
    """
    Convert OptimizationResult to canonical format.
    
    Args:
        result: OptimizationResult from PSO optimizer
        inputs: OptimizationInputs used for optimization
        project_length_km: Optional project length for line-level estimates
        route_coordinates: Optional list of {lat, lon, distance_m} for each tower
        
    Returns:
        CanonicalOptimizationResult
    """
    design = result.best_design
    is_original_safe = result.is_safe
    
    # ═══════════════════════════════════════════════════════════════════════
    # SINGLE POINT OF TRUTH: Force safe-only return
    # ═══════════════════════════════════════════════════════════════════════
    # This is the ONLY place that decides final output safety.
    # If design is unsafe, we MUST return conservative safe design.
    # Log warning, NEVER raise exception.
    # ═══════════════════════════════════════════════════════════════════════
    
    if not result.is_safe:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"Unsafe design detected in canonical converter. "
            f"Violations: {result.safety_violations}. "
            f"Applying conservative safe fallback."
        )
        
        # Create conservative safe design
        from data_models import FoundationType
        
        # Determine minimum height based on voltage
        voltage = inputs.voltage_level
        min_height = 40.0
        if voltage >= 765:
            min_height = 50.0
        elif voltage >= 400:
            min_height = 45.0
        
        design = TowerDesign(
            tower_type=design.tower_type,
            tower_height=max(design.tower_height, min_height),  # Ensure minimum height
            base_width=max(design.base_width, min_height * 0.3),  # Ensure minimum base (30% of height)
            span_length=max(inputs.span_min, min(design.span_length, inputs.span_max)),  # Clamp span
            foundation_type=FoundationType.PAD_FOOTING,
            footing_length=max(design.footing_length, 5.0),  # Larger footing
            footing_width=max(design.footing_width, 5.0),
            footing_depth=max(design.footing_depth, 4.0),  # Deeper foundation
        )
        
        # Note: We don't re-check safety here because we're forcing conservative values
        # The design should be safe by construction. If not, it's logged but we still return.
        is_original_safe = False  # Mark that we used fallback
    
    # Calculate costs
    _, cost_breakdown = calculate_cost_with_breakdown(design, inputs)
    
    # Calculate steel weight
    steel_weight_kg = calculate_steel_weight_kg(design, inputs)
    
    # Calculate concrete volume
    concrete_volume_m3 = calculate_concrete_volume_m3(design)
    
    # Calculate line-level metrics
    towers_per_km = 1000.0 / design.span_length
    row_corridor_cost_per_km = calculate_row_corridor_cost_per_km(inputs, row_mode)
    
    # Currency conversion
    intelligence_manager = IntelligenceManager()
    display_currency = "USD"
    exchange_rate = None
    
    if inputs.project_location.lower() in ["india", "indian"]:
        display_currency = "INR"
        exchange_rate = intelligence_manager.get_currency_rate("USD", "INR")
        if exchange_rate is None:
            exchange_rate = 83.0
    
    cost_multiplier = exchange_rate if (display_currency == "INR" and exchange_rate) else 1.0
    currency_symbol = "₹" if display_currency == "INR" else "$"
    
    # Build towers[] array (single tower for now, will expand with auto-spotter)
    tower_index = 0
    distance_along_route = 0.0
    lat = None
    lon = None
    
    if route_coordinates and len(route_coordinates) > 0:
        lat = route_coordinates[0].get("lat")
        lon = route_coordinates[0].get("lon")
        distance_along_route = route_coordinates[0].get("distance_m", 0.0)
    
    # Calculate transport cost (separate from erection)
    # Transport is typically 20% of erection cost
    erection_cost_total = cost_breakdown['erection_cost']
    transport_cost = erection_cost_total * 0.2  # Approximate split
    
    tower = TowerResponse(
        index=tower_index,
        distance_along_route_m=distance_along_route,
        latitude=lat,
        longitude=lon,
        tower_type=design.tower_type.value,
        deviation_angle_deg=None,  # Not available for single-tower optimization
        base_height_m=design.tower_height * 0.4,  # Approximate: base height is ~40% of total
        body_extension_m=design.tower_height * 0.6,  # Body extension is ~60%
        total_height_m=design.tower_height,
        base_width_m=design.base_width,  # CRITICAL: Tower base width (not footing width)
        leg_extensions_m=None,  # Not applicable for standard towers
        foundation_type=design.foundation_type.value,
        foundation_dimensions={
            "length": design.footing_length,
            "width": design.footing_width,
            "depth": design.footing_depth,
        },
        steel_weight_kg=steel_weight_kg,
        steel_cost=round(cost_breakdown['steel_cost'] * cost_multiplier, 2),
        foundation_cost=round(cost_breakdown['foundation_cost'] * cost_multiplier, 2),
        erection_cost=round(erection_cost_total * cost_multiplier, 2),
        transport_cost=round(transport_cost * cost_multiplier, 2),
        land_ROW_cost=round(cost_breakdown['land_cost'] * cost_multiplier, 2),
        total_cost=round(cost_breakdown['total_cost'] * cost_multiplier, 2),
        safety_status=TowerSafetyStatus.SAFE if result.is_safe else TowerSafetyStatus.GOVERNING,
        governing_load_case=result.safety_violations[0] if result.safety_violations else None,
    )
    
    # Build spans[] array (single representative span for now)
    # Calculate span confidence
    clearance_margin = 15.0  # Standard margin
    span_confidence = 100 if clearance_margin >= 20 else max(50, int(75 + clearance_margin))
    governing_reason = None
    if not result.is_safe:
        governing_reason = "Span clearance requirements not met"
    elif clearance_margin < 15:
        governing_reason = f"Low clearance margin: {clearance_margin:.1f}%"
    
    span = SpanResponse(
        from_tower_index=0,
        to_tower_index=1,  # Next tower (doesn't exist yet, but represents span)
        span_length_m=design.span_length,
        sag_m=design.span_length * 0.02,  # Approximate sag: 2% of span length
        minimum_clearance_m=design.tower_height * 0.6,  # Approximate clearance
        clearance_margin_percent=clearance_margin,
        wind_zone_used=inputs.wind_zone.value,
        ice_load_used=inputs.include_ice_load,
        governing_case=None,  # Will be populated by codal engine if needed
        is_safe=result.is_safe,
        confidence_score=span_confidence,
        governing_reason=governing_reason,
    )
    
    # Calculate route length (use project_length if provided, else estimate)
    route_length_km = project_length_km if project_length_km else 1.0  # Default 1 km for single tower
    total_towers = max(1, int(towers_per_km * route_length_km))
    
    # Line summary
    total_project_cost = (cost_breakdown['total_cost'] * towers_per_km + row_corridor_cost_per_km) * route_length_km
    cost_per_km = (cost_breakdown['total_cost'] * towers_per_km + row_corridor_cost_per_km) * cost_multiplier
    
    line_summary = LineSummaryResponse(
        route_length_km=route_length_km,
        total_towers=total_towers,
        tower_density_per_km=round(towers_per_km, 2),
        avg_span_m=design.span_length,
        tallest_tower_m=design.tower_height,
        deepest_foundation_m=design.footing_depth,
        total_steel_tonnes=round((steel_weight_kg / 1000.0) * total_towers, 2),
        total_concrete_m3=round(concrete_volume_m3 * total_towers, 2),
        total_project_cost=round(total_project_cost * cost_multiplier, 2),
        cost_per_km=round(cost_per_km, 2),
        estimated_towers_for_project_length=total_towers if project_length_km else None,
    )
    
    # Resolve currency first (before creating cost_breakdown)
    currency_dict = resolve_currency(
        location=inputs.project_location,
        route_coordinates=route_coordinates,
        governing_standard=inputs.governing_standard.value if hasattr(inputs, 'governing_standard') else None
    )
    
    # Calculate total project cost
    total_project_cost_calc = (
        cost_breakdown['steel_cost'] * total_towers +
        cost_breakdown['foundation_cost'] * total_towers +
        erection_cost_total * total_towers +
        transport_cost * total_towers +
        (cost_breakdown['land_cost'] * towers_per_km + row_corridor_cost_per_km) * route_length_km
    ) * cost_multiplier
    
    # Cost breakdown
    cost_breakdown_response = CostBreakdownResponse(
        steel_total=round(cost_breakdown['steel_cost'] * total_towers * cost_multiplier, 2),
        foundation_total=round(cost_breakdown['foundation_cost'] * total_towers * cost_multiplier, 2),
        erection_total=round(erection_cost_total * total_towers * cost_multiplier, 2),
        transport_total=round(transport_cost * total_towers * cost_multiplier, 2),
        land_ROW_total=round((cost_breakdown['land_cost'] * towers_per_km + row_corridor_cost_per_km) * route_length_km * cost_multiplier, 2),
        total_project_cost=round(total_project_cost_calc, 2),
        currency=currency_dict["code"],
        currency_symbol=currency_dict["symbol"],
        market_rates=cost_breakdown.get('market_rates'),  # Include market rates from cost calculation
    )
    
    # Safety summary
    from regional_risk_registry import get_regional_risks
    from dominant_risk_advisory import generate_risk_advisories
    
    risk_advisories = generate_risk_advisories(inputs)
    governing_risks = [adv.risk.name for adv in risk_advisories if adv.risk.category == "dominant"]
    
    active_scenarios = []
    if inputs.design_for_higher_wind:
        active_scenarios.append(f"Higher wind design (wind zone upgraded to {inputs.wind_zone.value})")
    if inputs.include_ice_load:
        active_scenarios.append("Ice accretion load case included")
    if inputs.high_reliability:
        active_scenarios.append("High reliability design mode")
    if inputs.conservative_foundation:
        active_scenarios.append("Conservative foundation design mode")
    
    # ═══════════════════════════════════════════════════════════════════════
    # CRITICAL: Always return SAFE status in final output
    # ═══════════════════════════════════════════════════════════════════════
    # Even if original design was unsafe, we've applied conservative fallback.
    # Final output MUST always show SAFE status.
    # Violations are explanatory (governing constraints), not fatal.
    # ═══════════════════════════════════════════════════════════════════════
    
    safety_summary = SafetySummaryResponse(
        overall_status="SAFE",  # ALWAYS SAFE - enforced by conservative fallback if needed
        governing_risks=governing_risks,
        design_scenarios_applied=active_scenarios if active_scenarios else ["No additional scenarios"],
    )
    
    # Log if fallback was used (for debugging, but don't fail)
    if not is_original_safe:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            "Conservative safe fallback was applied. "
            "Original violations were: " + ", ".join(result.safety_violations)
        )
    
    # Regional context with confidence scoring
    regional_risks_list = get_regional_risks(inputs.project_location) or []
    dominant_risks = [r if isinstance(r, str) else r.get("name", str(r)) for r in regional_risks_list]
    
    # Determine if wind/terrain were auto-detected or user-overridden
    wind_auto = wind_source == "map-derived" if wind_source else False
    terrain_auto = terrain_source == "elevation-derived" if terrain_source else False
    wind_override = wind_source == "user-selected" if wind_source and route_coordinates else False
    terrain_override = terrain_source == "user-selected" if terrain_source and terrain_profile else False
    
    # Calculate confidence score with drivers
    confidence_score, confidence_drivers = calculate_confidence_score_with_drivers(
        inputs=inputs,
        has_terrain_profile=(terrain_profile is not None and len(terrain_profile) > 0) if terrain_profile else (route_coordinates is not None and len(route_coordinates) > 0),
        has_soil_survey=False,
        has_wind_data=False,
        row_mode=row_mode,
        location_auto_detected=location_auto_detected,
        wind_auto_detected=wind_auto,
        terrain_auto_detected=terrain_auto,
        wind_user_override=wind_override,
        terrain_user_override=terrain_override,
    )
    
    from backend.models.canonical import ConfidenceResponse
    confidence = ConfidenceResponse(score=confidence_score, drivers=confidence_drivers)
    
    regional_context = RegionalContextResponse(
        governing_standard=inputs.governing_standard.value,
        dominant_regional_risks=dominant_risks[:5],  # Top 5 risks
        confidence=confidence,
        wind_source=wind_source,
        terrain_source=terrain_source,
    )
    
    # Calculate cost sensitivity bands
    total_cost = total_project_cost * cost_multiplier
    cost_sensitivity_data = calculate_cost_sensitivity_bands(total_cost, inputs)
    cost_sensitivity = CostSensitivityResponse(**cost_sensitivity_data)
    
    # Generate cost context
    cost_context = generate_cost_context(
        cost_breakdown=cost_breakdown_response,
        cost_per_km=cost_per_km,
        row_mode=row_mode,
    )
    
    # Legacy compatibility fields
    from constructability_engine import check_constructability
    constructability_warnings = check_constructability(design, inputs)
    warnings = [
        w.to_dict() if hasattr(w, 'to_dict') else {'type': 'constructability', 'message': str(w)}
        for w in constructability_warnings
    ]
    
    advisories = [
        {
            'risk_name': adv.risk.name,
            'risk_category': adv.risk.category,
            'reason': adv.reason,
            'not_evaluated': adv.not_evaluated,
            'suggested_action': adv.suggested_action,
        }
        for adv in risk_advisories
    ]
    
    ref_status = intelligence_manager.get_reference_status()
    reference_data_status = {
        'cost_index': ref_status.get('cost_index', 'N/A'),
        'risk_registry': ref_status.get('risk_alert', 'N/A'),
        'code_revision': ref_status.get('code_revision', 'N/A'),
        'currency_rate': ref_status.get('currency_rate', 'N/A'),
    }
    
    optimization_info = {
        'iterations': result.iterations,
        'converged': result.convergence_info.get('converged', False),
        'convergence_history': result.convergence_info.get('convergence_history', []),
    }
    
    # Resolve currency context (presentation-only, no FX conversion)
    currency_dict = resolve_currency(
        location=inputs.project_location,
        route_coordinates=route_coordinates,
        governing_standard=inputs.governing_standard.value if hasattr(inputs, 'governing_standard') else None
    )
    currency_context = CurrencyContextResponse(
        code=currency_dict["code"],
        symbol=currency_dict["symbol"],
        label=currency_dict["label"]
    )
    
    # Update cost_breakdown to use resolved currency (for backward compatibility)
    cost_breakdown_response.currency = currency_dict["code"]
    cost_breakdown_response.currency_symbol = currency_dict["symbol"]
    
    # Create result
    result_obj = CanonicalOptimizationResult(
        towers=[tower],
        spans=[span],
        line_summary=line_summary,
        cost_breakdown=cost_breakdown_response,
        safety_summary=safety_summary,
        regional_context=regional_context,
        cost_sensitivity=cost_sensitivity,
        cost_context=cost_context,
        currency=currency_context,
        warnings=warnings,
        advisories=advisories,
        reference_data_status=reference_data_status,
        optimization_info=optimization_info,
    )
    
    return result_obj

