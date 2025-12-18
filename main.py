"""
Main Entry Point for Transmission Tower Optimization System.

This module orchestrates the optimization process:
1. Accepts user input
2. Resolves governing code automatically
3. Runs PSO optimization
4. Outputs best design, cost, and safety confirmation

THIS IS A DECISION-SUPPORT TOOL.
IT DOES NOT REPLACE ENGINEERS.
"""

import argparse
import sys
from typing import Optional

from data_models import (
    OptimizationInputs, DesignStandard, TowerType,
    TerrainType, WindZone, SoilCategory
)
from location_to_code import get_governing_standard
from codal_engine import (
    ISEngine, IECEngine, EurocodeEngine, ASCEEngine
)
from pso_optimizer import PSOOptimizer
from cost_engine import calculate_cost, calculate_cost_with_breakdown, check_cost_sanity
from constructability_engine import check_constructability, format_warnings
from regional_risk_registry import get_regional_risks, format_regional_risks
from dominant_risk_advisory import generate_risk_advisories, format_risk_advisories
from intelligence.intelligence_manager import IntelligenceManager

# Import service for shared logic (CLI still works independently)
try:
    from backend.services.optimizer_service import run_optimization as run_optimization_service
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False


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


def parse_terrain_type(terrain_str: str) -> TerrainType:
    """Parse terrain type string."""
    terrain_map = {
        'flat': TerrainType.FLAT,
        'rolling': TerrainType.ROLLING,
        'mountainous': TerrainType.MOUNTAINOUS,
        'desert': TerrainType.DESERT,
    }
    terrain_str_lower = terrain_str.lower()
    if terrain_str_lower not in terrain_map:
        raise ValueError(f"Unknown terrain type: {terrain_str}")
    return terrain_map[terrain_str_lower]


def parse_wind_zone(wind_str: str) -> WindZone:
    """Parse wind zone string."""
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
    wind_str_lower = wind_str.lower()
    if wind_str_lower not in wind_map:
        raise ValueError(f"Unknown wind zone: {wind_str}")
    return wind_map[wind_str_lower]


def parse_soil_category(soil_str: str) -> SoilCategory:
    """Parse soil category string."""
    soil_map = {
        'soft': SoilCategory.SOFT,
        'medium': SoilCategory.MEDIUM,
        'hard': SoilCategory.HARD,
        'rock': SoilCategory.ROCK,
    }
    soil_str_lower = soil_str.lower()
    if soil_str_lower not in soil_map:
        raise ValueError(f"Unknown soil category: {soil_str}")
    return soil_map[soil_str_lower]


def parse_tower_type(tower_str: str) -> TowerType:
    """Parse tower type string."""
    tower_map = {
        'suspension': TowerType.SUSPENSION,
        'angle': TowerType.ANGLE,
        'tension': TowerType.TENSION,
        'strain': TowerType.TENSION,
        'dead_end': TowerType.DEAD_END,
        'deadend': TowerType.DEAD_END,
    }
    tower_str_lower = tower_str.lower()
    if tower_str_lower not in tower_map:
        raise ValueError(f"Unknown tower type: {tower_str}")
    return tower_map[tower_str_lower]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Transmission Tower Design Optimization System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This is a DECISION-SUPPORT TOOL.
It does NOT replace engineers.
All designs must be reviewed by qualified engineers before construction.

Example usage:
  python main.py --location "India" --voltage 400 --terrain flat --wind zone_2 --soil medium --tower suspension
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--location',
        type=str,
        required=True,
        help='Project location (country/region, e.g., "India", "UAE", "USA")'
    )
    parser.add_argument(
        '--voltage',
        type=float,
        required=True,
        help='Voltage level in kV (e.g., 132, 220, 400, 765)'
    )
    parser.add_argument(
        '--terrain',
        type=str,
        required=True,
        choices=['flat', 'rolling', 'mountainous', 'desert'],
        help='Terrain type'
    )
    parser.add_argument(
        '--wind',
        type=str,
        required=True,
        help='Wind zone (zone_1, zone_2, zone_3, zone_4, or 1, 2, 3, 4)'
    )
    parser.add_argument(
        '--soil',
        type=str,
        required=True,
        choices=['soft', 'medium', 'hard', 'rock'],
        help='Soil category'
    )
    
    # Optional arguments
    parser.add_argument(
        '--tower',
        type=str,
        default='suspension',
        help='Tower type (default: suspension)'
    )
    parser.add_argument(
        '--span-min',
        type=float,
        default=250.0,
        help='Minimum span length in meters (default: 250)'
    )
    parser.add_argument(
        '--span-max',
        type=float,
        default=450.0,
        help='Maximum span length in meters (default: 450)'
    )
    parser.add_argument(
        '--particles',
        type=int,
        default=30,
        help='Number of PSO particles (default: 30)'
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=100,
        help='Maximum PSO iterations (default: 100)'
    )
    
    # Design scenario toggles (optional)
    parser.add_argument(
        '--design-for-higher-wind',
        action='store_true',
        help='Design for higher wind (upgrade wind zone by +1)'
    )
    parser.add_argument(
        '--include-ice-load',
        action='store_true',
        help='Include ice accretion load case'
    )
    parser.add_argument(
        '--high-reliability',
        action='store_true',
        help='High reliability design mode (increased safety factors)'
    )
    parser.add_argument(
        '--conservative-foundation',
        action='store_true',
        help='Conservative foundation design mode (stricter footing limits)'
    )
    
    args = parser.parse_args()
    
    # Parse inputs
    try:
        terrain_type = parse_terrain_type(args.terrain)
        wind_zone = parse_wind_zone(args.wind)
        soil_category = parse_soil_category(args.soil)
        tower_type = parse_tower_type(args.tower)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Handle higher wind design scenario
    design_wind_zone = wind_zone
    if args.design_for_higher_wind:
        # Upgrade wind zone by +1
        wind_zone_map = {
            WindZone.ZONE_1: WindZone.ZONE_2,
            WindZone.ZONE_2: WindZone.ZONE_3,
            WindZone.ZONE_3: WindZone.ZONE_4,
            WindZone.ZONE_4: WindZone.ZONE_4,  # Already maximum
        }
        design_wind_zone = wind_zone_map.get(wind_zone, wind_zone)
    
    # Resolve governing standard
    try:
        governing_standard = get_governing_standard(args.location)
        print(f"\n{'='*70}")
        print(f"PROJECT LOCATION: {args.location}")
        print(f"GOVERNING STANDARD: {governing_standard.value}")
        if args.design_for_higher_wind:
            print(f"WIND ZONE: {wind_zone.value} (design upgraded to {design_wind_zone.value} by user request)")
        else:
            print(f"WIND ZONE: {wind_zone.value}")
        print(f"{'='*70}\n")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Create optimization inputs
    inputs = OptimizationInputs(
        project_location=args.location,
        voltage_level=args.voltage,
        terrain_type=terrain_type,
        wind_zone=design_wind_zone,  # Use design wind zone (may be upgraded)
        soil_category=soil_category,
        span_min=args.span_min,
        span_max=args.span_max,
        governing_standard=governing_standard,
        design_for_higher_wind=args.design_for_higher_wind,
        include_ice_load=args.include_ice_load,
        high_reliability=args.high_reliability,
        conservative_foundation=args.conservative_foundation,
    )
    
    # Create codal engine
    codal_engine = create_codal_engine(governing_standard)
    print(f"Using codal engine: {codal_engine.standard_name}\n")
    
    # Create optimizer
    optimizer = PSOOptimizer(
        codal_engine=codal_engine,
        inputs=inputs,
        num_particles=args.particles,
        max_iterations=args.iterations,
    )
    
    # Run optimization
    print("Running optimization...")
    print("-" * 70)
    result = optimizer.optimize(tower_type=tower_type)
    
    # Output results
    print("\n" + "="*70)
    print("OPTIMIZATION RESULTS")
    print("="*70)
    
    if result.is_safe:
        print(f"\nBest Design:")
        print(f"  Tower Type: {result.best_design.tower_type.value}")
        print(f"  Tower Height: {result.best_design.tower_height:.2f} m")
        print(f"  Base Width: {result.best_design.base_width:.2f} m")
        print(f"  Span Length: {result.best_design.span_length:.2f} m")
        print(f"  Foundation Type: {result.best_design.foundation_type.value}")
        print(f"  Footing Length: {result.best_design.footing_length:.2f} m")
        print(f"  Footing Width: {result.best_design.footing_width:.2f} m")
        print(f"  Footing Depth: {result.best_design.footing_depth:.2f} m")
        
        # Calculate cost with breakdown
        _, cost_breakdown = calculate_cost_with_breakdown(result.best_design, inputs)
        
        # Calculate line-level economics
        towers_per_km = 1000.0 / result.best_design.span_length
        
        # Calculate ROW costs
        from cost_engine import calculate_row_corridor_cost_per_km
        row_corridor_cost_per_km = calculate_row_corridor_cost_per_km(inputs)
        row_tower_footprint_per_km = cost_breakdown['land_cost'] * towers_per_km
        
        # Total per-km cost (includes ROW corridor cost)
        per_km_cost = (cost_breakdown['total_cost'] * towers_per_km) + row_corridor_cost_per_km
        
        # Currency conversion for display (India only)
        intelligence_manager = IntelligenceManager()
        display_currency = "USD"
        exchange_rate = None
        
        if inputs.project_location.lower() in ["india", "indian"]:
            display_currency = "INR"
            exchange_rate = intelligence_manager.get_currency_rate("USD", "INR")
            if exchange_rate is None:
                exchange_rate = 83.0  # Default
        
        # Format costs based on display currency
        if display_currency == "INR" and exchange_rate:
            steel_display = cost_breakdown['steel_cost'] * exchange_rate
            foundation_display = cost_breakdown['foundation_cost'] * exchange_rate
            erection_display = cost_breakdown['erection_cost'] * exchange_rate
            land_display = cost_breakdown['land_cost'] * exchange_rate
            total_display = cost_breakdown['total_cost'] * exchange_rate
            currency_symbol = "₹"
        else:
            steel_display = cost_breakdown['steel_cost']
            foundation_display = cost_breakdown['foundation_cost']
            erection_display = cost_breakdown['erection_cost']
            land_display = cost_breakdown['land_cost']
            total_display = cost_breakdown['total_cost']
            currency_symbol = "$"
        
        print(f"\nCost Breakdown (PER-TOWER):")
        print(f"  Steel Cost:           {currency_symbol}{steel_display:,.2f} {display_currency}")
        print(f"  Foundation Cost:      {currency_symbol}{foundation_display:,.2f} {display_currency}")
        print(f"  Transport & Erection: {currency_symbol}{erection_display:,.2f} {display_currency}")
        print(f"  Land / ROW Cost:      {currency_symbol}{land_display:,.2f} {display_currency}")
        print(f"  Total Cost:           {currency_symbol}{total_display:,.2f} {display_currency}")
        
        # Show regional multipliers
        if 'multipliers' in cost_breakdown:
            mult = cost_breakdown['multipliers']
            print(f"\n  Regional Multipliers ({cost_breakdown['region'].upper()}):")
            print(f"    Steel:      ×{mult['steel']:.2f}")
            print(f"    Materials:  ×{mult['materials']:.2f}")
            print(f"    Labor:      ×{mult['labor']:.2f}")
            print(f"    Access:     ×{mult['access']:.2f}")
        
        print(f"\n{'='*70}")
        print("LINE-LEVEL ECONOMIC SUMMARY")
        print("="*70)
        # Currency conversion for line-level summary
        if inputs.project_location.lower() in ["india", "indian"]:
            display_currency_line = "INR"
            exchange_rate_line = intelligence_manager.get_currency_rate("USD", "INR")
            currency_version = intelligence_manager.get_currency_version()
            if exchange_rate_line is None:
                exchange_rate_line = 83.0
                currency_version = "default"
            currency_symbol_line = "₹"
        else:
            display_currency_line = "USD"
            exchange_rate_line = 1.0
            currency_version = None
            currency_symbol_line = "$"
        
        # Format line-level costs
        if display_currency_line == "INR" and exchange_rate_line:
            cost_per_tower_display = cost_breakdown['total_cost'] * exchange_rate_line
            row_corridor_display = row_corridor_cost_per_km * exchange_rate_line
            row_tower_footprint_display = row_tower_footprint_per_km * exchange_rate_line
            total_cost_display = per_km_cost * exchange_rate_line
        else:
            cost_per_tower_display = cost_breakdown['total_cost']
            row_corridor_display = row_corridor_cost_per_km
            row_tower_footprint_display = row_tower_footprint_per_km
            total_cost_display = per_km_cost
        
        print(f"  Span Length:                {result.best_design.span_length:.2f} m")
        print(f"  Towers per km:              {towers_per_km:.3f}")
        print(f"  Cost per tower:             {currency_symbol_line}{cost_per_tower_display:,.2f} {display_currency_line}")
        print(f"  ROW Corridor Cost per km:   {currency_symbol_line}{row_corridor_display:,.2f} {display_currency_line}/km")
        print(f"  ROW Tower Footprint per km: {currency_symbol_line}{row_tower_footprint_display:,.2f} {display_currency_line}/km")
        print(f"  TOTAL Estimated Cost per km: {currency_symbol_line}{total_cost_display:,.2f} {display_currency_line}/km")
        
        if display_currency_line == "INR" and exchange_rate_line:
            print(f"\n  Exchange Rate Used: 1 USD = {exchange_rate_line:.2f} INR")
            if currency_version:
                print(f"  FX Reference Version: {currency_version}")
        
        print(f"\n  NOTE: Line-level cost per kilometer is the optimization objective.")
        print(f"  NOTE: ROW corridor cost dominates land economics in dense regions.")
        print("="*70)
        
        # Cost sanity check
        is_reasonable, warning = check_cost_sanity(
            cost_breakdown['total_cost'],
            inputs.voltage_level,
            result.best_design.tower_type.value
        )
        if not is_reasonable:
            print(f"\n  {warning}")
        
        print(f"\nSafety Status:")
        print(f"  Is Safe: YES")
        print(f"  No violations - design complies with {governing_standard.value}")
        
        # Constructability warnings
        constructability_warnings = check_constructability(result.best_design, inputs)
        print(f"\n{format_warnings(constructability_warnings)}")
        
        # Regional risk context
        regional_risks = get_regional_risks(inputs.project_location)
        if regional_risks:
            print(f"\n{format_regional_risks(regional_risks)}")
        
        # Dominant regional risk advisories
        risk_advisories = generate_risk_advisories(inputs)
        if risk_advisories:
            print(f"\n{format_risk_advisories(risk_advisories)}")
        
        # Design scenarios applied
        # Reference data status
        ref_status = intelligence_manager.get_reference_status()
        
        print(f"\n{'='*70}")
        print("REFERENCE DATA STATUS")
        print("="*70)
        print(f"  Cost indices: {ref_status.get('cost_index', 'none')}")
        print(f"  Risk registry: {ref_status.get('risk_alert', 'none')}")
        print(f"  Code revisions: {ref_status.get('code_revision', 'none')}")
        print(f"  FX reference: {ref_status.get('currency_rate', 'none')}")
        print(f"\n  Engineering calculations are NOT")
        print(f"  automatically modified by live data.")
        print("="*70)
        
        print(f"\n{'='*70}")
        print("DESIGN SCENARIOS APPLIED")
        print("="*70)
        active_scenarios = []
        if inputs.design_for_higher_wind:
            active_scenarios.append(f"Higher wind design (wind zone upgraded from {wind_zone.value} to {inputs.wind_zone.value})")
        if inputs.include_ice_load:
            active_scenarios.append("Ice accretion load case included")
        if inputs.high_reliability:
            active_scenarios.append("High reliability design mode (increased safety factors)")
        if inputs.conservative_foundation:
            active_scenarios.append("Conservative foundation design mode (stricter footing limits)")
        
        if active_scenarios:
            for scenario in active_scenarios:
                print(f"• {scenario}")
        else:
            print("No additional design scenarios applied.")
        print("="*70)
        
        print(f"\nOptimization Info:")
        print(f"  Iterations: {result.iterations}")
    else:
        print(f"\nNO FEASIBLE DESIGN FOUND WITHIN CURRENT SEARCH SPACE")
        print(f"\nClosest Candidate (REJECTED – UNSAFE):")
        print(f"  Tower Type: {result.best_design.tower_type.value}")
        print(f"  Tower Height: {result.best_design.tower_height:.2f} m")
        print(f"  Base Width: {result.best_design.base_width:.2f} m")
        print(f"  Span Length: {result.best_design.span_length:.2f} m")
        print(f"  Foundation Type: {result.best_design.foundation_type.value}")
        print(f"  Footing Length: {result.best_design.footing_length:.2f} m")
        print(f"  Footing Width: {result.best_design.footing_width:.2f} m")
        print(f"  Footing Depth: {result.best_design.footing_depth:.2f} m")
        
        print(f"\nSafety Status:")
        print(f"  Is Safe: NO")
        print(f"  Violations:")
        for i, violation in enumerate(result.safety_violations, 1):
            print(f"    {i}. {violation}")
        
        print(f"\nOptimization Info:")
        print(f"  Iterations: {result.iterations}")
        print(f"  Note: Cost shown is penalty value, not actual design cost")
    
    print("\n" + "="*70)
    print("IMPORTANT: This is a DECISION-SUPPORT TOOL.")
    print("All designs must be reviewed by qualified engineers.")
    print("="*70 + "\n")
    
    return 0 if result.is_safe else 1


if __name__ == '__main__':
    sys.exit(main())

