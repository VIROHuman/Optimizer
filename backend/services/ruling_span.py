"""
Ruling Span Approximation Module.

FIX 3: Provides ruling span approximation for strain sections.

CRITICAL: This is an APPROXIMATION, not full cable equilibrium.
- Does NOT solve broken wire cases
- Does NOT solve longitudinal load redistribution
- Does NOT attempt multi-span equilibrium

This module groups suspension towers into strain sections and computes
equivalent ruling span for sag estimation and tension-related advisories.
"""

from typing import List, Dict, Any, Optional
from data_models import TowerDesign, TowerType


def calculate_ruling_span(span_lengths: List[float]) -> float:
    """
    Calculate equivalent ruling span for a strain section.
    
    Formula: Sr = sqrt(sum(L_i^3) / sum(L_i))
    
    Where:
        Sr = Ruling span
        L_i = Individual span lengths in the strain section
    
    Args:
        span_lengths: List of span lengths in meters
        
    Returns:
        Equivalent ruling span in meters
        
    Note:
        This is an approximation. Full multi-span equilibrium is not solved.
    """
    if not span_lengths:
        return 0.0
    
    if len(span_lengths) == 1:
        return span_lengths[0]
    
    # Calculate sum of L^3 and sum of L
    sum_l3 = sum(span ** 3 for span in span_lengths)
    sum_l = sum(span_lengths)
    
    if sum_l == 0:
        return 0.0
    
    # Ruling span formula
    ruling_span = (sum_l3 / sum_l) ** 0.5
    
    return ruling_span


def group_towers_into_strain_sections(
    towers: List[Dict[str, Any]],
    spans: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Group towers into strain sections.
    
    A strain section is a group of suspension towers bounded by:
    - Dead-end towers
    - Angle/tension towers (significant deviation)
    - Route start/end
    
    Args:
        towers: List of tower objects with tower_type
        spans: List of span objects with from_tower_index, to_tower_index, span_length_m
        
    Returns:
        List of strain section dictionaries with:
        - section_index: int
        - start_tower_index: int
        - end_tower_index: int
        - tower_indices: List[int]
        - span_lengths: List[float]
        - ruling_span_m: float
    """
    if not towers or not spans:
        return []
    
    strain_sections = []
    current_section_towers = []
    current_section_spans = []
    section_index = 0
    
    # Create span lookup by from_tower_index
    span_lookup = {}
    for span in spans:
        from_idx = span.get('from_tower_index') or span.get('from')
        to_idx = span.get('to_tower_index') or span.get('to')
        span_length = span.get('span_length_m') or span.get('length')
        if from_idx is not None and span_length is not None:
            span_lookup[from_idx] = {
                'to': to_idx,
                'length': span_length
            }
    
    i = 0
    while i < len(towers):
        tower = towers[i]
        tower_type = tower.get('tower_type') or tower.get('type', 'suspension')
        tower_index = tower.get('index') or i
        
        # Check if this tower ends a strain section
        is_section_end = (
            tower_type in ['dead_end', 'angle', 'tension'] or
            i == 0 or  # Route start
            i == len(towers) - 1  # Route end
        )
        
        if is_section_end and current_section_towers:
            # End current section
            if len(current_section_spans) > 0:
                span_lengths = [s['length'] for s in current_section_spans]
                ruling_span = calculate_ruling_span(span_lengths)
                
                strain_sections.append({
                    'section_index': section_index,
                    'start_tower_index': current_section_towers[0],
                    'end_tower_index': current_section_towers[-1],
                    'tower_indices': current_section_towers.copy(),
                    'span_lengths': span_lengths,
                    'ruling_span_m': ruling_span,
                    'num_spans': len(span_lengths),
                })
                section_index += 1
            
            # Start new section
            current_section_towers = []
            current_section_spans = []
        
        # Add tower to current section if it's a suspension tower
        if tower_type == 'suspension':
            current_section_towers.append(tower_index)
            
            # Add span if available
            if tower_index in span_lookup:
                span_info = span_lookup[tower_index]
                current_section_spans.append({
                    'from': tower_index,
                    'to': span_info['to'],
                    'length': span_info['length']
                })
        else:
            # Non-suspension tower - add to section but mark as boundary
            if current_section_towers:
                current_section_towers.append(tower_index)
        
        i += 1
    
    # Handle final section
    if current_section_towers and current_section_spans:
        span_lengths = [s['length'] for s in current_section_spans]
        ruling_span = calculate_ruling_span(span_lengths)
        
        strain_sections.append({
            'section_index': section_index,
            'start_tower_index': current_section_towers[0],
            'end_tower_index': current_section_towers[-1],
            'tower_indices': current_section_towers.copy(),
            'span_lengths': span_lengths,
            'ruling_span_m': ruling_span,
            'num_spans': len(span_lengths),
        })
    
    return strain_sections


def get_ruling_span_advisory(
    ruling_span_m: float,
    voltage_level: float
) -> Optional[str]:
    """
    Generate advisory message based on ruling span.
    
    Args:
        ruling_span_m: Ruling span in meters
        voltage_level: Voltage level in kV
        
    Returns:
        Advisory message or None
    """
    # Typical ruling span ranges by voltage
    typical_ranges = {
        132: (300, 400),
        220: (350, 450),
        400: (400, 500),
        765: (450, 550),
        900: (500, 600),
    }
    
    # Find appropriate range
    voltage_key = 132
    for v in sorted(typical_ranges.keys()):
        if voltage_level >= v:
            voltage_key = v
    
    min_typical, max_typical = typical_ranges[voltage_key]
    
    if ruling_span_m < min_typical:
        return f"Ruling span ({ruling_span_m:.0f}m) is below typical range ({min_typical}-{max_typical}m) for {voltage_key}kV. Consider longer spans to reduce tower count."
    elif ruling_span_m > max_typical:
        return f"Ruling span ({ruling_span_m:.0f}m) exceeds typical range ({min_typical}-{max_typical}m) for {voltage_key}kV. Verify conductor tension and sag limits."
    
    return None

