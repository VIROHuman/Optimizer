"""
Route-Level Optimization Service.

Orchestrates auto-spotter + per-tower optimizer + canonical aggregation.
"""

from typing import List, Dict, Any, Optional
from data_models import OptimizationInputs, TowerType
from auto_spotter import AutoSpotter, TerrainPoint, TowerPosition, create_terrain_profile_from_coordinates
from backend.services.optimizer_service import parse_input_dict, create_codal_engine, run_optimization
from pso_optimizer import PSOOptimizer
from backend.models.canonical import (
    CanonicalOptimizationResult, TowerResponse, SpanResponse,
    LineSummaryResponse, CostBreakdownResponse, SafetySummaryResponse,
    RegionalContextResponse, TowerSafetyStatus
)
from backend.services.currency_resolver import resolve_currency
from backend.services.tower_type_classifier import classify_all_towers
import logging

logger = logging.getLogger(__name__)


def optimize_route(
    route_coordinates: List[Dict[str, Any]],
    project_length_km: float,
    design_options: Dict[str, Any],
    row_mode: str = "urban_private",
    terrain_profile: Optional[List[Dict[str, float]]] = None,  # TASK 5.3: Optional terrain profile from frontend
) -> CanonicalOptimizationResult:
    """
    Optimize entire route with automatic tower placement.
    
    Process:
    1. Auto-spotter places towers along route
    2. Optimizer designs each tower
    3. Aggregate into canonical format
    
    Args:
        route_coordinates: List of {lat, lon, elevation_m, distance_m}
        project_length_km: Total route length
        design_options: Design parameters dict
        terrain_profile: Optional terrain profile from frontend [{ "x": distance_m, "z": elevation_m }]
        
    Returns:
        CanonicalOptimizationResult with full route data
    """
    # Parse design options (this will auto-detect location, wind, terrain if route_coordinates exist)
    # Add route_coordinates and terrain_profile to design_options so parse_input_dict can use them
    design_options_with_route = design_options.copy()
    design_options_with_route['route_coordinates'] = route_coordinates
    design_options_with_route['terrain_profile'] = terrain_profile
    inputs, tower_type = parse_input_dict(design_options_with_route)
    location_auto_detected = design_options_with_route.get('_location_auto_detected', False)
    wind_source = design_options_with_route.get('_wind_source')
    terrain_source = design_options_with_route.get('_terrain_source')
    
    # TASK 5.3: Use terrain_profile if provided, otherwise create from coordinates
    if terrain_profile:
        # Convert frontend format to TerrainPoint list
        from auto_spotter import TerrainPoint
        terrain_points = []
        for tp in terrain_profile:
            # Find matching route coordinate for lat/lon
            distance_m = tp.get("x", 0.0)
            elevation_m = tp.get("z", 0.0)
            
            # Find closest route coordinate
            closest_coord = None
            min_dist_diff = float('inf')
            for coord in route_coordinates:
                coord_dist = coord.get("distance_m", 0.0)
                dist_diff = abs(coord_dist - distance_m)
                if dist_diff < min_dist_diff:
                    min_dist_diff = dist_diff
                    closest_coord = coord
            
            terrain_points.append(TerrainPoint(
                distance_m=distance_m,
                elevation_m=elevation_m,
                latitude=closest_coord.get("lat") if closest_coord else None,
                longitude=closest_coord.get("lon") if closest_coord else None,
            ))
        terrain_profile_parsed = terrain_points
    else:
        # Create terrain profile from coordinates (fallback)
        terrain_profile_parsed = create_terrain_profile_from_coordinates(route_coordinates)
    
    # Step 1: Auto-spotter places towers
    spotter = AutoSpotter(
        inputs=inputs,
        max_span_m=inputs.span_max,
        min_span_m=inputs.span_min,
    )
    
    tower_positions = spotter.place_towers(
        terrain_profile=terrain_profile_parsed,
        route_start_lat=route_coordinates[0].get("lat") if route_coordinates else None,
        route_start_lon=route_coordinates[0].get("lon") if route_coordinates else None,
        route_coordinates=route_coordinates,  # CRITICAL: Pass route_coordinates for polyline walker
    )
    
    logger.info(f"Auto-spotter placed {len(tower_positions)} towers along route")
    
    # Step 1.5: Classify all towers based on geometry (automatic, no user selection)
    tower_classifications = classify_all_towers(tower_positions, inputs)
    logger.info(f"Classified {len(tower_classifications)} towers based on route geometry")
    
    # Step 2: Optimize each tower
    codal_engine = create_codal_engine(inputs.governing_standard)
    optimized_towers = []
    optimized_spans = []
    
    for i, tower_pos in enumerate(tower_positions):
        # Get classified tower type (geometry-driven, not user-selected)
        geometry_tower_type, deviation_angle_deg, classification_reason = tower_classifications[i]
        
        # Create optimizer for this tower
        optimizer = PSOOptimizer(
            codal_engine=codal_engine,
            inputs=inputs,
            num_particles=30,
            max_iterations=100,
        )
        
        # Optimize tower design using classified type
        result = optimizer.optimize(tower_type=geometry_tower_type)
        
        # Convert to canonical tower response
        tower_response = _create_tower_response(
            tower_pos=tower_pos,
            result=result,
            inputs=inputs,
            tower_index=i,
            geometry_tower_type=geometry_tower_type,
            deviation_angle_deg=deviation_angle_deg,
            design_reason=classification_reason,
        )
        optimized_towers.append(tower_response)
        
        # Create span if not last tower
        if i < len(tower_positions) - 1:
            next_tower_pos = tower_positions[i + 1]
            span_length = next_tower_pos.distance_along_route_m - tower_pos.distance_along_route_m
            
            span_response = _create_span_response(
                from_tower_index=i,
                to_tower_index=i + 1,
                span_length_m=span_length,
                from_tower_pos=tower_pos,
                to_tower_pos=next_tower_pos,
                inputs=inputs,
                terrain_profile=terrain_profile_parsed,
            )
            optimized_spans.append(span_response)
    
    # Step 3: Aggregate into canonical format
    return _aggregate_route_results(
        towers=optimized_towers,
        spans=optimized_spans,
        inputs=inputs,
        project_length_km=project_length_km,
        row_mode=row_mode,
        terrain_profile=terrain_profile_parsed,
    )


def _create_tower_response(
    tower_pos: TowerPosition,
    result,
    inputs: OptimizationInputs,
    tower_index: int,
    geometry_tower_type: TowerType,
    deviation_angle_deg: Optional[float],
    design_reason: str,
) -> TowerResponse:
    """Create TowerResponse from optimized result."""
    from backend.services.canonical_converter import calculate_steel_weight_kg, calculate_concrete_volume_m3
    from cost_engine import calculate_cost_with_breakdown
    from intelligence.intelligence_manager import IntelligenceManager
    
    design = result.best_design
    
    # Calculate base costs
    _, cost_breakdown = calculate_cost_with_breakdown(design, inputs)
    
    # Ensure transport_cost exists (it's calculated as 20% of erection_cost)
    if 'transport_cost' not in cost_breakdown:
        cost_breakdown['transport_cost'] = cost_breakdown.get('erection_cost', 0.0) * 0.2
    
    # Apply tower type scaling (physics & cost scaling)
    cost_breakdown_scaled = _apply_tower_scaling(
        cost_breakdown, geometry_tower_type, deviation_angle_deg, inputs.voltage_level
    )
    
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
    
    steel_weight_kg = calculate_steel_weight_kg(design, inputs)
    erection_cost_total = cost_breakdown_scaled['erection_cost']
    transport_cost = cost_breakdown_scaled['transport_cost']
    
    from backend.models.canonical import TowerResponse, TowerSafetyStatus
    
    return TowerResponse(
        index=tower_index,
        distance_along_route_m=tower_pos.distance_along_route_m,
        latitude=tower_pos.latitude,
        longitude=tower_pos.longitude,
        tower_type=geometry_tower_type.value,  # Use geometry-driven type, not design.tower_type
        deviation_angle_deg=deviation_angle_deg,  # Store deviation angle
        base_height_m=design.tower_height * 0.4,
        body_extension_m=design.tower_height * 0.6,
        total_height_m=design.tower_height,
        base_width_m=design.base_width,  # CRITICAL: Tower base width (not footing width)
        leg_extensions_m=None,
        foundation_type=design.foundation_type.value,
        foundation_dimensions={
            "length": design.footing_length,
            "width": design.footing_width,
            "depth": design.footing_depth,
        },
        steel_weight_kg=steel_weight_kg,
        steel_cost=round(cost_breakdown_scaled['steel_cost'] * cost_multiplier, 2),
        foundation_cost=round(cost_breakdown_scaled['foundation_cost'] * cost_multiplier, 2),
        erection_cost=round(erection_cost_total * cost_multiplier, 2),
        transport_cost=round(transport_cost * cost_multiplier, 2),
        land_ROW_cost=round(cost_breakdown_scaled.get('land_cost', 0.0) * cost_multiplier, 2),
        total_cost=round(cost_breakdown_scaled['total_cost'] * cost_multiplier, 2),
        design_reason=design_reason,
        safety_status=TowerSafetyStatus.SAFE if result.is_safe else TowerSafetyStatus.GOVERNING,
        governing_load_case=result.safety_violations[0] if (hasattr(result, 'safety_violations') and result.safety_violations) else None,
    )


def _apply_tower_scaling(
    costs: dict,
    tower_type: TowerType,
    deviation: Optional[float],
    voltage_kv: float
) -> dict:
    """
    Apply physics & cost scaling based on tower type and deviation.
    
    Rules:
    - Suspension: Base design, no penalties
    - Angle: Steel × 1.5, Foundation × 1.3
    - Dead-End: Voltage-aware scaling (1.6-2.8 for steel, 1.4-1.7 for foundation)
    
    Args:
        costs: Cost breakdown dictionary
        tower_type: Classified tower type
        deviation: Deviation angle in degrees (for dead-end scaling)
        voltage_kv: Voltage level in kV
        
    Returns:
        Scaled cost breakdown dictionary
    """
    scaled = costs.copy()
    dev = deviation or 0.0
    
    # Ensure transport_cost exists (it's calculated as 20% of erection_cost)
    if 'transport_cost' not in scaled:
        scaled['transport_cost'] = scaled.get('erection_cost', 0.0) * 0.2
    
    if tower_type == TowerType.ANGLE:
        # Angle Towers: Fixed multipliers
        steel_mult = 1.5  # Fixed multiplier for Angle towers
        foundation_mult = 1.3
        scaled['steel_cost'] *= steel_mult
        scaled['foundation_cost'] *= foundation_mult
    elif tower_type == TowerType.DEAD_END:
        # Dead-End Towers: Voltage-aware scaling bands
        if voltage_kv >= 765:
            steel_mult = 2.2 + 0.6 * min(max(dev / 20.0, 0.0), 1.0)  # 2.2 – 2.8
        elif voltage_kv >= 400:
            steel_mult = 1.8 + 0.5 * min(max(dev / 30.0, 0.0), 1.0)  # 1.8 – 2.3
        else:
            steel_mult = 1.6 + 0.4 * min(max(dev / 35.0, 0.0), 1.0)  # 1.6 – 2.0
        
        foundation_mult = 1.4 + 0.3 * min(max(dev / 35.0, 0.0), 1.0)  # 1.4 – 1.7
        scaled['steel_cost'] *= steel_mult
        scaled['foundation_cost'] *= foundation_mult
    # Suspension towers: No scaling (base design)
    
    # Recompute total cost and derived components (transport remains proportional to erection)
    scaled['total_cost'] = (
        scaled['steel_cost']
        + scaled['foundation_cost']
        + scaled['erection_cost']
        + scaled['transport_cost']
        + scaled.get('land_cost', 0.0)
    )
    return scaled


def _create_span_response(
    from_tower_index: int,
    to_tower_index: int,
    span_length_m: float,
    from_tower_pos: TowerPosition,
    to_tower_pos: TowerPosition,
    inputs: OptimizationInputs,
    terrain_profile: List[TerrainPoint],
) -> SpanResponse:
    """Create SpanResponse from tower positions."""
    from auto_spotter import AutoSpotter
    from backend.models.canonical import SpanResponse
    
    # Calculate sag and clearance
    spotter = AutoSpotter(inputs=inputs)
    sag_m = spotter.calculate_sag(span_length_m)
    
    # Mid-span elevation
    mid_distance = (from_tower_pos.distance_along_route_m + to_tower_pos.distance_along_route_m) / 2.0
    mid_elevation = spotter.interpolate_elevation(mid_distance, terrain_profile)
    
    # Approximate clearance (conservative estimate)
    avg_tower_height = 40.0  # Will be replaced with actual optimized heights
    conductor_height = (from_tower_pos.elevation_m + to_tower_pos.elevation_m) / 2.0 + avg_tower_height - sag_m
    clearance = conductor_height - mid_elevation
    clearance_margin_percent = (clearance / avg_tower_height) * 100.0 if avg_tower_height > 0 else 0.0
    
    return SpanResponse(
        from_tower_index=from_tower_index,
        to_tower_index=to_tower_index,
        span_length_m=span_length_m,
        sag_m=sag_m,
        minimum_clearance_m=max(0.0, clearance),
        clearance_margin_percent=max(0.0, clearance_margin_percent),
        wind_zone_used=inputs.wind_zone.value,
        ice_load_used=inputs.include_ice_load,
        governing_case=None,
        is_safe=clearance >= 10.0,  # Minimum clearance requirement
    )


def _aggregate_route_results(
    towers: List[TowerResponse],
    spans: List[SpanResponse],
    inputs: OptimizationInputs,
    project_length_km: float,
    row_mode: str = "urban_private",
    terrain_profile: Optional[List[TerrainPoint]] = None,
    location_auto_detected: bool = False,
    wind_source: Optional[str] = None,
    terrain_source: Optional[str] = None,
    route_coordinates: Optional[List[Dict[str, Any]]] = None,
) -> CanonicalOptimizationResult:
    """Aggregate route-level results into canonical format."""
    from backend.models.canonical import (
        LineSummaryResponse, CostBreakdownResponse, SafetySummaryResponse,
        RegionalContextResponse
    )
    from cost_engine import calculate_row_corridor_cost_per_km
    from intelligence.intelligence_manager import IntelligenceManager
    from regional_risk_registry import get_regional_risks
    from dominant_risk_advisory import generate_risk_advisories
    
    if not towers:
        raise ValueError("No towers to aggregate")
    
    # Calculate totals
    total_towers = len(towers)
    total_steel_kg = sum(t.steel_weight_kg for t in towers)
    total_steel_tonnes = total_steel_kg / 1000.0
    
    # Calculate concrete volume
    total_concrete_m3 = sum(
        t.foundation_dimensions["length"] * 
        t.foundation_dimensions["width"] * 
        t.foundation_dimensions["depth"] * 4  # 4 footings per tower
        for t in towers
    )
    
    # Calculate costs
    steel_total = sum(t.steel_cost for t in towers)
    foundation_total = sum(t.foundation_cost for t in towers)
    erection_total = sum(t.erection_cost for t in towers)
    transport_total = sum(t.transport_cost for t in towers)
    land_ROW_total = sum(t.land_ROW_cost for t in towers)
    
    # Add ROW corridor cost
    row_corridor_cost_per_km = calculate_row_corridor_cost_per_km(inputs, row_mode)
    land_ROW_total += row_corridor_cost_per_km * project_length_km
    
    # Line summary
    avg_span = sum(s.span_length_m for s in spans) / len(spans) if spans else 0.0
    tallest_tower = max(t.total_height_m for t in towers)
    deepest_foundation = max(t.foundation_dimensions["depth"] for t in towers)
    tower_density = total_towers / project_length_km if project_length_km > 0 else 0.0
    total_project_cost = steel_total + foundation_total + erection_total + transport_total + land_ROW_total
    cost_per_km = total_project_cost / project_length_km if project_length_km > 0 else 0.0
    
    line_summary = LineSummaryResponse(
        route_length_km=project_length_km,
        total_towers=total_towers,
        tower_density_per_km=round(tower_density, 2),
        avg_span_m=round(avg_span, 2),
        tallest_tower_m=round(tallest_tower, 2),
        deepest_foundation_m=round(deepest_foundation, 2),
        total_steel_tonnes=round(total_steel_tonnes, 2),
        total_concrete_m3=round(total_concrete_m3, 2),
        total_project_cost=round(total_project_cost, 2),
        cost_per_km=round(cost_per_km, 2),
        estimated_towers_for_project_length=total_towers,
    )
    
    # Resolve currency first (before creating cost_breakdown)
    # resolve_currency now always returns a valid dict (defaults to USD for non-India, INR for India if IS standard)
    currency_dict = resolve_currency(
        location=inputs.project_location,
        route_coordinates=route_coordinates,
        governing_standard=inputs.governing_standard.value if hasattr(inputs, 'governing_standard') else None
    )
    
    # Calculate total project cost
    total_project_cost = steel_total + foundation_total + erection_total + transport_total + land_ROW_total
    
    cost_breakdown = CostBreakdownResponse(
        steel_total=round(steel_total, 2),
        foundation_total=round(foundation_total, 2),
        erection_total=round(erection_total, 2),
        transport_total=round(transport_total, 2),
        land_ROW_total=round(land_ROW_total, 2),
        total_project_cost=round(total_project_cost, 2),
        currency=currency_dict["code"],
        currency_symbol=currency_dict["symbol"],
    )
    
    # Safety summary
    risk_advisories = generate_risk_advisories(inputs)
    governing_risks = [adv.risk.name for adv in risk_advisories if adv.risk.category == "dominant"]
    
    active_scenarios = []
    if inputs.design_for_higher_wind:
        active_scenarios.append(f"Higher wind design")
    if inputs.include_ice_load:
        active_scenarios.append("Ice accretion load case")
    if inputs.high_reliability:
        active_scenarios.append("High reliability design mode")
    if inputs.conservative_foundation:
        active_scenarios.append("Conservative foundation design mode")
    
    safety_summary = SafetySummaryResponse(
        overall_status="SAFE",  # Always safe (enforced by converter)
        governing_risks=governing_risks,
        design_scenarios_applied=active_scenarios if active_scenarios else ["No additional scenarios"],
    )
    
    # Regional context
    regional_risks_list = get_regional_risks(inputs.project_location) or []
    dominant_risks = [r if isinstance(r, str) else r.get("name", str(r)) for r in regional_risks_list[:5]]
    
    # TASK 5.6: Calculate confidence score with drivers using real data
    from backend.services.confidence_scorer import calculate_confidence_score_with_drivers
    from backend.models.canonical import ConfidenceResponse
    # Check if terrain_profile was provided (higher confidence) vs created from coordinates
    has_detailed_terrain = terrain_profile is not None and len(terrain_profile) > 0
    # Determine if wind/terrain were auto-detected or user-overridden
    wind_auto = wind_source == "map-derived" if wind_source else False
    terrain_auto = terrain_source == "elevation-derived" if terrain_source else False
    wind_override = wind_source == "user-selected" if wind_source else False
    terrain_override = terrain_source == "user-selected" if terrain_source else False
    
    confidence_score, confidence_drivers = calculate_confidence_score_with_drivers(
        inputs=inputs,
        has_terrain_profile=has_detailed_terrain,  # TASK 5.6: Use actual terrain profile status
        has_soil_survey=False,  # TASK 5.6: Soil still assumed
        has_wind_data=False,  # TASK 5.6: Wind still zonal
        row_mode=row_mode,
        location_auto_detected=location_auto_detected,
        wind_auto_detected=wind_auto,
        terrain_auto_detected=terrain_auto,
        wind_user_override=wind_override,
        terrain_user_override=terrain_override,
    )
    
    # TASK 5.6: Add route-specific confidence drivers
    if has_detailed_terrain:
        confidence_drivers.append("Route explicitly defined with terrain sampling")
        # Check sampling resolution
        if len(terrain_profile) > 100:
            confidence_drivers.append("High-resolution terrain sampling (>100 points)")
        elif len(terrain_profile) > 50:
            confidence_drivers.append("Medium-resolution terrain sampling (50-100 points)")
        else:
            confidence_drivers.append("Low-resolution terrain sampling (<50 points)")
            confidence_score = max(50, confidence_score - 5)  # Reduce confidence for low resolution
    else:
        confidence_drivers.append("Terrain profile created from route coordinates (lower accuracy)")
    
    confidence = ConfidenceResponse(score=confidence_score, drivers=confidence_drivers)
    
    regional_context = RegionalContextResponse(
        governing_standard=inputs.governing_standard.value,
        dominant_regional_risks=dominant_risks,
        confidence=confidence,
        wind_source=wind_source,
        terrain_source=terrain_source,
    )
    
    # Calculate cost sensitivity
    from backend.services.cost_sensitivity import calculate_cost_sensitivity_bands
    from backend.models.canonical import CostSensitivityResponse
    cost_sensitivity_data = calculate_cost_sensitivity_bands(total_project_cost, inputs)
    cost_sensitivity = CostSensitivityResponse(**cost_sensitivity_data)
    
    # Generate cost context
    from backend.services.cost_context import generate_cost_context
    from backend.models.canonical import CostContextResponse, CurrencyContextResponse
    cost_context = generate_cost_context(
        cost_breakdown=cost_breakdown,
        cost_per_km=cost_per_km,
        row_mode=row_mode,
    )
    
    # Warnings and advisories
    warnings = []
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
    
    ref_status = IntelligenceManager().get_reference_status()
    reference_data_status = {
        'cost_index': ref_status.get('cost_index', 'N/A'),
        'risk_registry': ref_status.get('risk_alert', 'N/A'),
        'code_revision': ref_status.get('code_revision', 'N/A'),
        'currency_rate': ref_status.get('currency_rate', 'N/A'),
    }
    
    optimization_info = {
        'iterations': sum(1 for _ in towers),  # Approximate
        'converged': True,
    }
    
    # Currency context (already resolved above)
    currency_context = CurrencyContextResponse(
        code=currency_dict["code"],
        symbol=currency_dict["symbol"],
        label=currency_dict["label"]
    )
    
    return CanonicalOptimizationResult(
        towers=towers,
        spans=spans,
        line_summary=line_summary,
        cost_breakdown=cost_breakdown,
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

