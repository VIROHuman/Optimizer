"""
Optimizer Service Module.

Extracts core optimization logic into a reusable service.
Used by both CLI (main.py) and API (api.py).
"""

from typing import Dict, Any, Optional
from data_models import (
    OptimizationInputs, DesignStandard, TowerType,
    TerrainType, WindZone, SoilCategory
)
from location_to_code import get_governing_standard
from codal_engine import (
    ISEngine, IECEngine, EurocodeEngine, ASCEEngine
)
from pso_optimizer import PSOOptimizer
from cost_engine import (
    calculate_cost_with_breakdown, 
    calculate_row_corridor_cost_per_km,
    check_cost_sanity
)
from constructability_engine import check_constructability
from regional_risk_registry import get_regional_risks
from dominant_risk_advisory import generate_risk_advisories
from intelligence.intelligence_manager import IntelligenceManager


def create_codal_engine(standard: DesignStandard):
    """
    Create appropriate codal engine instance.
    
    Args:
        standard: DesignStandard enum
        
    Returns:
        CodalEngine instance
    """
    engines = {
        DesignStandard.IS: ISEngine,
        DesignStandard.IEC: IECEngine,
        DesignStandard.EUROCODE: EurocodeEngine,
        DesignStandard.ASCE: ASCEEngine,
    }
    
    engine_class = engines.get(standard)
    if engine_class is None:
        raise ValueError(f"Unsupported design standard: {standard}")
    
    return engine_class()


def parse_input_dict(input_dict: Dict[str, Any]) -> tuple[OptimizationInputs, TowerType]:
    """
    Parse input dictionary into OptimizationInputs and TowerType.
    
    Args:
        input_dict: Dictionary with keys:
            - location: str
            - voltage: int
            - terrain: str
            - wind: str
            - soil: str
            - tower: str
            - design_for_higher_wind: bool
            - include_ice_load: bool
            - conservative_foundation: bool
            - high_reliability: bool (optional)
            - span_min: float (optional)
            - span_max: float (optional)
            - particles: int (optional)
            - iterations: int (optional)
    
    Returns:
        Tuple of (OptimizationInputs, TowerType)
    """
    # Parse terrain
    terrain_map = {
        'flat': TerrainType.FLAT,
        'rolling': TerrainType.ROLLING,
        'mountainous': TerrainType.MOUNTAINOUS,
        'desert': TerrainType.DESERT,
    }
    terrain_type = terrain_map.get(input_dict['terrain'].lower())
    if terrain_type is None:
        raise ValueError(f"Unknown terrain type: {input_dict['terrain']}")
    
    # Parse wind zone
    wind_map = {
        'zone_1': WindZone.ZONE_1,
        'zone_2': WindZone.ZONE_2,
        'zone_3': WindZone.ZONE_3,
        'zone_4': WindZone.ZONE_4,
        '1': WindZone.ZONE_1,
        '2': WindZone.ZONE_2,
        '3': WindZone.ZONE_3,
        '4': WindZone.ZONE_4,
    }
    wind_zone = wind_map.get(input_dict['wind'].lower())
    if wind_zone is None:
        raise ValueError(f"Unknown wind zone: {input_dict['wind']}")
    
    # Handle higher wind design scenario
    design_wind_zone = wind_zone
    if input_dict.get('design_for_higher_wind', False):
        wind_zone_map = {
            WindZone.ZONE_1: WindZone.ZONE_2,
            WindZone.ZONE_2: WindZone.ZONE_3,
            WindZone.ZONE_3: WindZone.ZONE_4,
            WindZone.ZONE_4: WindZone.ZONE_4,
        }
        design_wind_zone = wind_zone_map.get(wind_zone, wind_zone)
    
    # Parse soil
    soil_map = {
        'soft': SoilCategory.SOFT,
        'medium': SoilCategory.MEDIUM,
        'hard': SoilCategory.HARD,
        'rock': SoilCategory.ROCK,
    }
    soil_category = soil_map.get(input_dict['soil'].lower())
    if soil_category is None:
        raise ValueError(f"Unknown soil category: {input_dict['soil']}")
    
    # Parse tower type
    tower_map = {
        'suspension': TowerType.SUSPENSION,
        'tension': TowerType.TENSION,
        'dead_end': TowerType.TENSION,  # Alias
    }
    tower_type = tower_map.get(input_dict['tower'].lower())
    if tower_type is None:
        raise ValueError(f"Unknown tower type: {input_dict['tower']}")
    
    # Resolve governing standard
    governing_standard = get_governing_standard(input_dict['location'])
    
    # Create optimization inputs
    inputs = OptimizationInputs(
        project_location=input_dict['location'],
        voltage_level=input_dict['voltage'],
        terrain_type=terrain_type,
        wind_zone=design_wind_zone,
        soil_category=soil_category,
        span_min=input_dict.get('span_min', 200.0),
        span_max=input_dict.get('span_max', 600.0),
        governing_standard=governing_standard,
        design_for_higher_wind=input_dict.get('design_for_higher_wind', False),
        include_ice_load=input_dict.get('include_ice_load', False),
        high_reliability=input_dict.get('high_reliability', False),
        conservative_foundation=input_dict.get('conservative_foundation', False),
    )
    
    return inputs, tower_type


def run_optimization(input_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run optimization and return structured results.
    
    Args:
        input_dict: Input parameters dictionary
        
    Returns:
        Dictionary with all optimization results
    """
    # Parse inputs
    inputs, tower_type = parse_input_dict(input_dict)
    
    # Create codal engine
    codal_engine = create_codal_engine(inputs.governing_standard)
    
    # Create optimizer
    optimizer = PSOOptimizer(
        codal_engine=codal_engine,
        inputs=inputs,
        num_particles=input_dict.get('particles', 30),
        max_iterations=input_dict.get('iterations', 100),
    )
    
    # Run optimization
    result = optimizer.optimize(tower_type=tower_type)
    
    # Build response
    response = {
        'project_context': {
            'location': inputs.project_location,
            'governing_standard': inputs.governing_standard.value,
            'voltage_level': inputs.voltage_level,
            'wind_zone': inputs.wind_zone.value,
            'terrain': inputs.terrain_type.value,
            'soil': inputs.soil_category.value,
        },
        'optimized_design': {
            'tower_type': result.best_design.tower_type.value,
            'tower_height': round(result.best_design.tower_height, 2),
            'base_width': round(result.best_design.base_width, 2),
            'span_length': round(result.best_design.span_length, 2),
            'foundation_type': result.best_design.foundation_type.value,
            'footing_length': round(result.best_design.footing_length, 2),
            'footing_width': round(result.best_design.footing_width, 2),
            'footing_depth': round(result.best_design.footing_depth, 2),
        },
        'safety_status': {
            'is_safe': result.is_safe,
            'violations': result.safety_violations if not result.is_safe else [],
        },
        'optimization_info': {
            'iterations': result.iterations,
            'converged': result.convergence_info.get('converged', False),
        },
    }
    
    # Add cost breakdown if safe
    if result.is_safe:
        _, cost_breakdown = calculate_cost_with_breakdown(result.best_design, inputs)
        
        # Calculate line-level economics
        towers_per_km = 1000.0 / result.best_design.span_length
        row_corridor_cost_per_km = calculate_row_corridor_cost_per_km(inputs)
        row_tower_footprint_per_km = cost_breakdown['land_cost'] * towers_per_km
        per_km_cost = (cost_breakdown['total_cost'] * towers_per_km) + row_corridor_cost_per_km
        
        # Currency conversion
        intelligence_manager = IntelligenceManager()
        display_currency = "USD"
        exchange_rate = None
        currency_version = None
        
        if inputs.project_location.lower() in ["india", "indian"]:
            display_currency = "INR"
            exchange_rate = intelligence_manager.get_currency_rate("USD", "INR")
            currency_version = intelligence_manager.get_currency_version()
            if exchange_rate is None:
                exchange_rate = 83.0
                currency_version = "default"
        
        # Format costs
        if display_currency == "INR" and exchange_rate:
            cost_multiplier = exchange_rate
            currency_symbol = "₹"
        else:
            cost_multiplier = 1.0
            currency_symbol = "$"
        
        response['cost_breakdown'] = {
            'steel_cost': round(cost_breakdown['steel_cost'] * cost_multiplier, 2),
            'foundation_cost': round(cost_breakdown['foundation_cost'] * cost_multiplier, 2),
            'erection_cost': round(cost_breakdown['erection_cost'] * cost_multiplier, 2),
            'land_cost': round(cost_breakdown['land_cost'] * cost_multiplier, 2),
            'total_cost': round(cost_breakdown['total_cost'] * cost_multiplier, 2),
            'currency': display_currency,
            'currency_symbol': currency_symbol,
            'exchange_rate': exchange_rate,
            'currency_version': currency_version,
        }
        
        if 'multipliers' in cost_breakdown:
            response['cost_breakdown']['regional_multipliers'] = {
                'steel': cost_breakdown['multipliers']['steel'],
                'materials': cost_breakdown['multipliers']['materials'],
                'labor': cost_breakdown['multipliers']['labor'],
                'access': cost_breakdown['multipliers']['access'],
                'region': cost_breakdown['region'],
            }
        
        response['line_level_summary'] = {
            'span_length': round(result.best_design.span_length, 2),
            'towers_per_km': round(towers_per_km, 3),
            'cost_per_tower': round(cost_breakdown['total_cost'] * cost_multiplier, 2),
            'row_corridor_cost_per_km': round(row_corridor_cost_per_km * cost_multiplier, 2),
            'row_tower_footprint_per_km': round(row_tower_footprint_per_km * cost_multiplier, 2),
            'total_cost_per_km': round(per_km_cost * cost_multiplier, 2),
            'currency': display_currency,
            'currency_symbol': currency_symbol,
        }
        
        # Constructability warnings
        constructability_warnings = check_constructability(result.best_design, inputs)
        response['warnings'] = [
            {
                'type': w['type'],
                'message': w['message'],
            }
            for w in constructability_warnings
        ]
        
        # Cost sanity check
        is_reasonable, warning = check_cost_sanity(
            cost_breakdown['total_cost'],
            inputs.voltage_level,
            result.best_design.tower_type.value
        )
        if not is_reasonable:
            response['warnings'].append({
                'type': 'cost_anomaly',
                'message': warning,
            })
    
    # Regional risks
    regional_risks = get_regional_risks(inputs.project_location)
    response['regional_risks'] = regional_risks if regional_risks else []
    
    # Dominant risk advisories
    risk_advisories = generate_risk_advisories(inputs)
    response['risk_advisories'] = [
        {
            'risk_name': adv.risk.name,
            'risk_category': adv.risk.category,
            'reason': adv.reason,
            'not_evaluated': adv.not_evaluated,
            'suggested_action': adv.suggested_action,
            'is_escalated': adv.is_escalated,
        }
        for adv in risk_advisories
    ]
    
    # Reference data status
    intelligence_manager = IntelligenceManager()
    ref_status = intelligence_manager.get_reference_status()
    response['reference_data_status'] = {
        'cost_index': ref_status.get('cost_index', 'N/A'),
        'risk_registry': ref_status.get('risk_alert', 'N/A'),
        'code_revision': ref_status.get('code_revision', 'N/A'),
        'currency_rate': ref_status.get('currency_rate', 'N/A'),
    }
    
    # Design scenarios applied
    active_scenarios = []
    if inputs.design_for_higher_wind:
        active_scenarios.append(f"Higher wind design (wind zone upgraded to {inputs.wind_zone.value})")
    if inputs.include_ice_load:
        active_scenarios.append("Ice accretion load case included")
    if inputs.high_reliability:
        active_scenarios.append("High reliability design mode (increased safety factors)")
    if inputs.conservative_foundation:
        active_scenarios.append("Conservative foundation design mode (stricter footing limits)")
    
    response['design_scenarios_applied'] = active_scenarios if active_scenarios else ["No additional design scenarios applied."]
    
    return response

