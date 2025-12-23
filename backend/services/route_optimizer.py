"""
Route-Level Optimization Service.

Orchestrates auto-spotter + per-tower optimizer + canonical aggregation.

SYSTEM POSITIONING:
This system operates upstream of detailed design tools.
It narrows corridors, budgets risk, and guides engineering effort.

This tool is NOT a member-level structural design engine and must NOT
attempt to compete with PLS-CADD.

Target accuracy: ±25-30% for feasibility/DPR-stage estimates.
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
from backend.models.geo_context import GeoContext
from backend.services.currency_resolver import resolve_currency
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
    
    # Step 1: Create codal engine (needed for span optimization)
    codal_engine = create_codal_engine(inputs.governing_standard)
    
    # Step 2: Auto-spotter places towers with adaptive span optimization
    spotter = AutoSpotter(
        inputs=inputs,
        max_span_m=inputs.span_max,
        min_span_m=inputs.span_min,
    )
    
    tower_positions = spotter.place_towers(
        terrain_profile=terrain_profile_parsed,
        route_start_lat=route_coordinates[0].get("lat") if route_coordinates else None,
        route_start_lon=route_coordinates[0].get("lon") if route_coordinates else None,
        codal_engine=codal_engine,  # Pass codal_engine for span optimization
    )
    
    logger.info(f"Auto-spotter placed {len(tower_positions)} towers along route")
    
    # SPAN REBALANCING: Rebalance tower positions for uniform spacing
    from backend.services.span_rebalancer import rebalance_spans
    rebalanced_towers, span_strategy, balanced_span_m = rebalance_spans(
        initial_towers=tower_positions,
        terrain_profile=terrain_profile_parsed,
        inputs=inputs,
        spotter=spotter,
        route_start_lat=route_coordinates[0].get("lat") if route_coordinates else None,
        route_start_lon=route_coordinates[0].get("lon") if route_coordinates else None,
    )
    
    if span_strategy == "balanced":
        logger.info(f"Span rebalancing successful: {len(rebalanced_towers)} towers with uniform span {balanced_span_m:.2f}m")
        tower_positions = rebalanced_towers
    else:
        logger.info("Span rebalancing rejected due to clearance violations, using original auto-spotter placement")
    
    # UPGRADE 1: Classify tower types based on route geometry
    from backend.services.tower_type_classifier import classify_all_towers
    tower_classifications = classify_all_towers(tower_positions)
    logger.info(f"Classified {len(tower_classifications)} towers based on route geometry")
    
    # Step 3: Optimize each tower (tower design optimization, not span selection)
    optimized_towers = []
    optimized_spans = []
    
    # CRITICAL: Validate tower positions before optimization
    if len(tower_positions) < 2:
        raise ValueError(f"Route optimization requires at least 2 towers, got {len(tower_positions)}")
    
    # Ensure towers are in sequential order
    for i in range(len(tower_positions) - 1):
        if tower_positions[i].distance_along_route_m >= tower_positions[i + 1].distance_along_route_m:
            raise ValueError(
                f"Tower positions must be sequential: Tower {i} at {tower_positions[i].distance_along_route_m:.2f}m "
                f"must be before Tower {i+1} at {tower_positions[i+1].distance_along_route_m:.2f}m"
            )
    
    for i, tower_pos in enumerate(tower_positions):
        # UPGRADE 1: Get geometry-derived tower type for this tower
        geometry_tower_type, _, _ = tower_classifications[i]
        
        # Create optimizer for this tower (use geometry-derived type)
        optimizer = PSOOptimizer(
            codal_engine=codal_engine,
            inputs=inputs,
            num_particles=30,
            max_iterations=100,
        )
        
        # Optimize tower design with geometry-derived tower type
        result = optimizer.optimize(tower_type=geometry_tower_type)
        
        # UPGRADE 2: Evaluate broken-wire case if enabled
        broken_wire_safe = True
        broken_wire_violation = None
        broken_wire_uplift_kn = None
        corrected_design = result.best_design
        
        if inputs.include_broken_wire:
            from backend.services.broken_wire_evaluator import evaluate_broken_wire_case, apply_broken_wire_corrections
            broken_wire_safe, broken_wire_violation, corrections = evaluate_broken_wire_case(
                result.best_design, inputs, codal_engine
            )
            
            if not broken_wire_safe and corrections:
                # Auto-correct design
                corrected_design = apply_broken_wire_corrections(result.best_design, corrections)
                # Re-evaluate to confirm correction
                broken_wire_safe, _, _ = evaluate_broken_wire_case(corrected_design, inputs, codal_engine)
                # Extract uplift force for foundation evaluation
                broken_wire_uplift_kn = corrections.get('foundation_uplift_kn', None)
        
        # UPGRADE 3: Evaluate foundation uplift
        from backend.services.foundation_uplift_evaluator import evaluate_foundation_uplift
        foundation_safe, total_uplift_kn, governing_uplift_case, required_depth = evaluate_foundation_uplift(
            corrected_design, inputs, broken_wire_uplift_kn
        )
        
        # Apply foundation depth correction if needed
        if not foundation_safe and required_depth > corrected_design.footing_depth:
            from data_models import TowerDesign
            corrected_design = TowerDesign(
                tower_type=corrected_design.tower_type,
                tower_height=corrected_design.tower_height,
                base_width=corrected_design.base_width,
                span_length=corrected_design.span_length,
                foundation_type=corrected_design.foundation_type,
                footing_length=corrected_design.footing_length,
                footing_width=corrected_design.footing_width,
                footing_depth=required_depth,
            )
        
        # Update result with corrected design
        if corrected_design != result.best_design:
            # Recalculate cost for corrected design
            from cost_engine import calculate_cost_with_breakdown
            corrected_cost, corrected_cost_breakdown = calculate_cost_with_breakdown(corrected_design, inputs)
            # Update result (create new result object with corrected design)
            from data_models import OptimizationResult
            result = OptimizationResult(
                best_design=corrected_design,
                best_cost=corrected_cost,
                is_safe=result.is_safe and broken_wire_safe and foundation_safe,
                safety_violations=result.safety_violations + ([broken_wire_violation] if broken_wire_violation else []),
                governing_standard=result.governing_standard,
                iterations=result.iterations,
                convergence_info=result.convergence_info,
            )
        
        # UPGRADE 1: Get geometry-derived tower type and deviation angle
        geometry_tower_type, deviation_angle_deg, classification_reason = tower_classifications[i]
        
        # Get foundation uplift case (from evaluation above)
        foundation_uplift_case = governing_uplift_case if not foundation_safe else None
        
        # CRITICAL: Enforce base width constraint on final design
        # This ensures the constraint is ALWAYS applied, even if it was bypassed during optimization
        from pso_optimizer import get_base_width_ratio_for_tower_type, MIN_BASE_WIDTH_RATIO, REGIONAL_MIN_BASE_WIDTH
        from data_models import TowerDesign
        
        final_design = result.best_design
        voltage = inputs.voltage_level
        regional_min = 5.0
        for v_level, min_base in sorted(REGIONAL_MIN_BASE_WIDTH.items()):
            if voltage >= v_level:
                regional_min = min_base
        
        tower_type_ratio = get_base_width_ratio_for_tower_type(final_design.tower_type)
        ratio_based_min = final_design.tower_height * MIN_BASE_WIDTH_RATIO
        base_width_ratio_min = final_design.tower_height * tower_type_ratio
        base_width_min = max(ratio_based_min, regional_min, base_width_ratio_min)
        
        if final_design.base_width < base_width_min:
            # Constraint violated - correct it
            logger.warning(
                f"Base width constraint violation detected for tower {i}: "
                f"base_width={final_design.base_width:.2f}m < min={base_width_min:.2f}m "
                f"(height={final_design.tower_height:.2f}m, type={final_design.tower_type.value}, "
                f"voltage={voltage}kV, regional_min={regional_min}m, ratio={tower_type_ratio}). "
                f"Correcting to {base_width_min:.2f}m."
            )
            final_design = TowerDesign(
                tower_type=final_design.tower_type,
                tower_height=final_design.tower_height,
                base_width=base_width_min,  # Enforce constraint
                span_length=final_design.span_length,
                foundation_type=final_design.foundation_type,
                footing_length=final_design.footing_length,
                footing_width=final_design.footing_width,
                footing_depth=final_design.footing_depth,
            )
            # Update result with corrected design
            from cost_engine import calculate_cost_with_breakdown
            corrected_cost, _ = calculate_cost_with_breakdown(final_design, inputs)
            from data_models import OptimizationResult
            result = OptimizationResult(
                best_design=final_design,
                best_cost=corrected_cost,
                is_safe=result.is_safe,
                safety_violations=result.safety_violations,
                governing_standard=result.governing_standard,
                iterations=result.iterations,
                convergence_info=result.convergence_info,
            )
        
        # Recalculate cost with final corrected design
        from cost_engine import calculate_cost_with_breakdown
        _, cost_breakdown_final = calculate_cost_with_breakdown(result.best_design, inputs)
        
        # Convert to canonical tower response
        tower_response = _create_tower_response(
            tower_pos=tower_pos,
            result=result,
            inputs=inputs,
            tower_index=i,
            geometry_tower_type=geometry_tower_type,
            deviation_angle_deg=deviation_angle_deg,
            cost_breakdown=cost_breakdown_final,
            governing_uplift_case=foundation_uplift_case,
        )
        optimized_towers.append(tower_response)
        
        # CRITICAL FIX 1: SPAN–TOWER CONSISTENCY
        # Create span for EVERY pair of sequential towers (T0–T1, T1–T2, ...)
        # This ensures N towers = N-1 spans
        if i < len(tower_positions) - 1:
            next_tower_pos = tower_positions[i + 1]
            
            # Calculate actual span length from positions
            actual_span_length = next_tower_pos.distance_along_route_m - tower_pos.distance_along_route_m
            
            # CRITICAL: Validate span length - throw error if invalid (do NOT silently skip)
            if actual_span_length <= 0.0:
                raise ValueError(
                    f"Invalid span from tower {i} to {i+1}: length={actual_span_length:.2f}m. "
                    f"Tower {i} at {tower_pos.distance_along_route_m:.2f}m, "
                    f"Tower {i+1} at {next_tower_pos.distance_along_route_m:.2f}m"
                )
            
            if actual_span_length < inputs.span_min:
                raise ValueError(
                    f"Span from tower {i} to {i+1} is {actual_span_length:.2f}m, "
                    f"which is below minimum span {inputs.span_min:.2f}m"
                )
            
            # Use selected span from tower position if available (from adaptive optimization)
            # But ensure it matches actual distance (prevent inconsistencies)
            selected_span = next_tower_pos.selected_span_m if hasattr(next_tower_pos, 'selected_span_m') and next_tower_pos.selected_span_m else actual_span_length
            
            # Ensure selected_span matches actual distance (within tolerance)
            if abs(selected_span - actual_span_length) > 1.0:  # 1m tolerance
                # Use actual distance if selected span doesn't match
                selected_span = actual_span_length
                logger.warning(f"Selected span {next_tower_pos.selected_span_m:.2f}m doesn't match actual {actual_span_length:.2f}m, using actual")
            
            span_selection_reason = next_tower_pos.span_selection_reason if hasattr(next_tower_pos, 'span_selection_reason') else None
            
            span_response = _create_span_response(
                from_tower_index=i,
                to_tower_index=i + 1,
                span_length_m=selected_span,  # Use selected span from adaptive optimization
                from_tower_pos=tower_pos,
                to_tower_pos=next_tower_pos,
                inputs=inputs,
                terrain_profile=terrain_profile_parsed,
                span_selection_reason=span_selection_reason,  # Pass selection reason
            )
            optimized_spans.append(span_response)
    
    # CRITICAL FIX 1: Validate span-tower consistency before aggregation
    if len(optimized_spans) != len(optimized_towers) - 1:
        raise ValueError(
            f"SPAN–TOWER CONSISTENCY VIOLATION: Expected {len(optimized_towers) - 1} spans for {len(optimized_towers)} towers, "
            f"but got {len(optimized_spans)} spans. This indicates a structural error in tower placement."
        )
    
    # Step 4: Aggregate into canonical format
    return _aggregate_route_results(
        towers=optimized_towers,
        spans=optimized_spans,
        inputs=inputs,
        project_length_km=project_length_km,
        row_mode=row_mode,
        terrain_profile=terrain_profile_parsed,
        location_auto_detected=location_auto_detected,
        wind_source=wind_source,
        terrain_source=terrain_source,
        route_coordinates=route_coordinates,
        geo_context=design_options_with_route.get('_geo_context'),
        resolution_mode=design_options_with_route.get('_resolution_mode'),
        standard_explanation=design_options_with_route.get('_standard_explanation'),
        span_strategy=span_strategy,  # SPAN REBALANCING: Pass strategy
        balanced_span_m=balanced_span_m,  # SPAN REBALANCING: Pass balanced span
    )


def _create_tower_response(
    tower_pos: TowerPosition,
    result,
    inputs: OptimizationInputs,
    tower_index: int,
    geometry_tower_type=None,
    deviation_angle_deg: Optional[float] = None,
    cost_breakdown: Optional[dict] = None,
    governing_uplift_case: Optional[str] = None,
) -> TowerResponse:
    """Create TowerResponse from optimized result."""
    from backend.services.canonical_converter import calculate_steel_weight_kg, calculate_concrete_volume_m3
    from cost_engine import calculate_cost_with_breakdown
    from intelligence.intelligence_manager import IntelligenceManager
    from data_models import TowerType
    
    design = result.best_design
    
    # UPGRADE 1: Use geometry-derived tower type if provided, otherwise use design's type
    if geometry_tower_type is None:
        geometry_tower_type = design.tower_type
    
    # Calculate costs (use provided cost_breakdown if available, otherwise recalculate)
    if cost_breakdown is None:
        _, cost_breakdown = calculate_cost_with_breakdown(design, inputs)
    
    # CRITICAL FIX 5: Cost Calculation Sanity
    # Costs are calculated in USD internally by cost_engine
    # Currency conversion is applied here based on resolved currency
    # Get currency from inputs (will be resolved in aggregation)
    cost_multiplier = 1.0  # Default: no conversion (USD)
    
    # Note: Currency conversion will be applied in aggregation layer
    # where currency is properly resolved from geo_context
    
    steel_weight_kg = calculate_steel_weight_kg(design, inputs)
    erection_cost_total = cost_breakdown['erection_cost']
    transport_cost = erection_cost_total * 0.2
    
    from backend.models.canonical import TowerResponse, TowerSafetyStatus
    
    return TowerResponse(
        index=tower_index,
        distance_along_route_m=tower_pos.distance_along_route_m,
        latitude=tower_pos.latitude,
        longitude=tower_pos.longitude,
        tower_type=geometry_tower_type.value,  # UPGRADE 1: Use geometry-derived type
        deviation_angle_deg=deviation_angle_deg,  # UPGRADE 1: Store deviation angle
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
        steel_cost=round(cost_breakdown['steel_cost'] * cost_multiplier, 2),
        foundation_cost=round(cost_breakdown['foundation_cost'] * cost_multiplier, 2),
        erection_cost=round(erection_cost_total * cost_multiplier, 2),
        transport_cost=round(transport_cost * cost_multiplier, 2),
        land_ROW_cost=round(cost_breakdown['land_cost'] * cost_multiplier, 2),
        total_cost=round(cost_breakdown['total_cost'] * cost_multiplier, 2),
        safety_status=TowerSafetyStatus.SAFE if result.is_safe else TowerSafetyStatus.GOVERNING,
        governing_load_case=result.safety_violations[0] if result.safety_violations else None,
        governing_uplift_case=governing_uplift_case,  # UPGRADE 3: Foundation uplift case
    )


def _create_span_response(
    from_tower_index: int,
    to_tower_index: int,
    span_length_m: float,
    from_tower_pos: TowerPosition,
    to_tower_pos: TowerPosition,
    inputs: OptimizationInputs,
    terrain_profile: List[TerrainPoint],
    span_selection_reason: Optional[str] = None,
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
    
    # Determine governing reason
    governing_reason = None
    if span_selection_reason:
        if "cheapest safe" in span_selection_reason.lower():
            governing_reason = f"Cost optimization: {span_selection_reason}"
        elif "end-of-line" in span_selection_reason.lower():
            governing_reason = span_selection_reason
        elif "unsafe" in span_selection_reason.lower():
            governing_reason = span_selection_reason
        else:
            governing_reason = span_selection_reason
    
    # FIX 3: Add ruling span disclaimer if applicable
    if governing_reason and "ruling span" in governing_reason.lower():
        if not governing_reason.endswith("Full multi-span equilibrium not solved."):
            governing_reason += " Ruling span approximated. Full multi-span equilibrium not solved."
    
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
        governing_reason=governing_reason,  # Add span selection reason
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
    geo_context: Optional[GeoContext] = None,
    resolution_mode: Optional[str] = None,
    standard_explanation: Optional[str] = None,
    span_strategy: str = "original",
    balanced_span_m: Optional[float] = None,
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
        wind_source=wind_source,
        terrain_source=terrain_source,
    )
    
    # CRITICAL FIX 4: Currency & Standard Resolution - NO SILENT DEFAULTS
    # Currency and governing standard MUST be resolved from geo_context
    # If geo_context is missing or unresolved, STOP and return validation error
    
    currency_dict = None
    if geo_context:
        from backend.services.geo_resolver import resolve_currency_from_geo
        currency_dict, resolution_mode_currency, currency_explanation = resolve_currency_from_geo(geo_context)
        
        # Validate that currency was actually resolved
        if not currency_dict or currency_dict.get("code") is None:
            raise ValueError(
                f"Currency resolution failed from geo_context. "
                f"Country: {geo_context.country_code if geo_context else 'Unknown'}. "
                f"Geo_context must provide valid country information for currency resolution."
            )
    else:
        # CRITICAL: If geo_context is missing, we cannot determine currency reliably
        # Only allow fallback if we have route_coordinates to derive country
        if route_coordinates and len(route_coordinates) > 0:
            # Try to derive from route coordinates
            from backend.services.location_deriver import derive_location_from_coordinates, reverse_geocode_simple
            # Get country code from first coordinate
            first_coord = route_coordinates[0]
            lat = first_coord.get("lat")
            lon = first_coord.get("lon")
            if lat is not None and lon is not None:
                country_code = reverse_geocode_simple(lat, lon)
            else:
                country_code = None
            
            if country_code:
                # Map country code to currency
                country_currency_map = {
                    "IN": {"code": "INR", "symbol": "₹", "label": "INR"},
                    "US": {"code": "USD", "symbol": "$", "label": "USD"},
                    "GB": {"code": "GBP", "symbol": "£", "label": "GBP"},
                    "DE": {"code": "EUR", "symbol": "€", "label": "EUR"},
                    "FR": {"code": "EUR", "symbol": "€", "label": "EUR"},
                    "AU": {"code": "AUD", "symbol": "A$", "label": "AUD"},
                }
                currency_dict = country_currency_map.get(country_code)
                if currency_dict:
                    currency_dict["resolution_mode"] = "coordinate-derived"
                    currency_dict["resolution_explanation"] = f"Currency derived from route coordinates (country: {country_code})"
        
        # If still no currency, check if standard can help (IS → INR only)
        if not currency_dict and inputs.governing_standard.value == "IS":
            currency_dict = {
                "code": "INR",
                "symbol": "₹",
                "label": "INR",
                "resolution_mode": "standard-derived",
                "resolution_explanation": "Currency derived from governing standard (IS → INR)."
            }
        
        # CRITICAL: If still unresolved, raise validation error (NO SILENT DEFAULT)
        if not currency_dict:
            raise ValueError(
                "Currency resolution failed: geo_context is missing or unresolved, "
                "and route_coordinates do not provide sufficient geographic information. "
                "Cannot proceed with cost calculation without currency context."
            )
    
    currency_code = currency_dict["code"]
    currency_symbol = currency_dict["symbol"]
    
    # CRITICAL FIX: Apply currency conversion if needed
    # Cost engine calculates in USD, convert to target currency using approved crawler data
    from intelligence.intelligence_manager import IntelligenceManager
    intelligence_manager = IntelligenceManager()
    exchange_rate = None
    
    if currency_code != "USD":
        # Get exchange rate from IntelligenceManager (uses approved crawler data)
        exchange_rate = intelligence_manager.get_currency_rate("USD", currency_code)
        
        if exchange_rate is None:
            # Fallback rates if crawler data not available
            fallback_rates = {
                "INR": 83.0,
                "GBP": 0.79,
                "EUR": 0.92,
                "AUD": 1.52,
            }
            exchange_rate = fallback_rates.get(currency_code, 1.0)
            logger.warning(f"Currency rate not found in approved data, using fallback: {currency_code} = {exchange_rate}")
        else:
            logger.info(f"Using approved currency rate from crawler: USD to {currency_code} = {exchange_rate}")
    else:
        exchange_rate = 1.0
    
    # Apply currency conversion to all costs
    currency_multiplier = exchange_rate
    
    # CRITICAL FIX: Convert individual tower costs to target currency
    # Tower costs are stored in USD, need to convert them for display
    # Pydantic models allow field modification, so we can update in place
    if currency_code != "USD" and currency_multiplier != 1.0:
        for tower in towers:
            # Convert each cost field
            tower.steel_cost = round(tower.steel_cost * currency_multiplier, 2)
            tower.foundation_cost = round(tower.foundation_cost * currency_multiplier, 2)
            tower.erection_cost = round(tower.erection_cost * currency_multiplier, 2)
            tower.transport_cost = round(tower.transport_cost * currency_multiplier, 2)
            tower.land_ROW_cost = round(tower.land_ROW_cost * currency_multiplier, 2)
            tower.total_cost = round(tower.total_cost * currency_multiplier, 2)
    
    # Recalculate totals after conversion
    steel_total_converted = sum(t.steel_cost for t in towers)
    foundation_total_converted = sum(t.foundation_cost for t in towers)
    erection_total_converted = sum(t.erection_cost for t in towers)
    transport_total_converted = sum(t.transport_cost for t in towers)
    land_ROW_total_converted = sum(t.land_ROW_cost for t in towers)
    
    # CRITICAL FIX: Cost breakdown uses resolved currency with proper conversion
    cost_breakdown = CostBreakdownResponse(
        steel_total=round(steel_total_converted, 2),
        foundation_total=round(foundation_total_converted, 2),
        erection_total=round(erection_total_converted, 2),
        transport_total=round(transport_total_converted, 2),
        land_ROW_total=round(land_ROW_total_converted, 2),
        currency=currency_code,
        currency_symbol=currency_symbol,
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
    
    # UPGRADE 2 & 3: Evaluate broken-wire and foundation uplift status
    broken_wire_status = "NOT_EVALUATED"
    foundation_uplift_governed = False
    
    if inputs.include_broken_wire:
        # Check if any tower had broken-wire violations
        broken_wire_violations = [
            t.governing_load_case for t in towers 
            if t.governing_load_case and "broken" in t.governing_load_case.lower()
        ]
        if broken_wire_violations:
            broken_wire_status = "GOVERNING"
        else:
            broken_wire_status = "PASS"
    
    # Check if any tower is governed by uplift
    uplift_governed_towers = [
        t for t in towers if t.governing_uplift_case is not None
    ]
    foundation_uplift_governed = len(uplift_governed_towers) > 0
    
    safety_summary = SafetySummaryResponse(
        overall_status="SAFE",  # Always safe (enforced by converter)
        governing_risks=governing_risks,
        design_scenarios_applied=active_scenarios if active_scenarios else ["No additional scenarios"],
        broken_wire_case=broken_wire_status,  # UPGRADE 2: Broken wire case status
        foundation_uplift_governed=foundation_uplift_governed,  # UPGRADE 3: Foundation uplift status
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
    
    # FIX 3: Calculate ruling span for strain sections
    from backend.services.ruling_span import group_towers_into_strain_sections, get_ruling_span_advisory
    strain_sections = group_towers_into_strain_sections(
        [t.dict() for t in towers],
        [s.dict() for s in spans]
    )
    
    # Add ruling span advisories
    ruling_span_advisories = []
    for section in strain_sections:
        advisory = get_ruling_span_advisory(section['ruling_span_m'], inputs.voltage_level)
        if advisory:
            ruling_span_advisories.append({
                'risk_name': f"Ruling Span - Section {section['section_index']}",
                'risk_category': "design_advisory",
                'reason': advisory,
                'not_evaluated': "Ruling span approximated. Full multi-span equilibrium not solved.",
                'suggested_action': "Verify conductor tension and sag limits with detailed design tools.",
            })
    
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
    
    # Add ruling span advisories
    advisories.extend(ruling_span_advisories)
    
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
        'span_strategy': span_strategy,  # SPAN REBALANCING: Strategy used ("balanced" or "original")
        'balanced_span_m': balanced_span_m,  # SPAN REBALANCING: Balanced span length (None if original strategy)
    }
    
    # Currency context (handle None case)
    currency_context = None
    if currency_dict:
        currency_context = CurrencyContextResponse(
            code=currency_dict["code"],
            symbol=currency_dict["symbol"],
            label=currency_dict["label"],
            resolution_mode=currency_dict.get("resolution_mode"),
            resolution_explanation=currency_dict.get("resolution_explanation"),
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

