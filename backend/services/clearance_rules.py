"""
Context-Aware Clearance Rules Library.

Provides voltage-indexed clearance requirements that adapt to:
- Global Standard (Country/Region)
- Line Voltage
- Obstacle Type (road, railway, river, power_line, default)
"""

from typing import Dict, Optional

# Voltage-Indexed Rules Library
# Format: {standard_code: {voltage_kv: {obstacle_type: clearance_m}}}
GLOBAL_CLEARANCE_RULES: Dict[str, Dict[int, Dict[str, float]]] = {
    # --- INDIA (IS 5613) ---
    'IS': {
        132: {'default': 6.1, 'road': 6.1, 'railway': 14.6, 'river': 6.1, 'power_line': 2.75},
        220: {'default': 7.0, 'road': 7.0, 'railway': 15.4, 'river': 7.0, 'power_line': 4.6},
        400: {'default': 8.84, 'road': 8.84, 'railway': 17.9, 'river': 8.84, 'power_line': 6.5},
    },
    # --- USA (NESC - Approx ft converted to m) ---
    'NESC': {
        132: {'default': 5.6, 'road': 6.7, 'railway': 9.5, 'river': 5.2, 'power_line': 2.5},
        220: {'default': 6.1, 'road': 7.5, 'railway': 10.5, 'river': 5.5, 'power_line': 3.5},
        400: {'default': 8.0, 'road': 9.5, 'railway': 12.5, 'river': 7.5, 'power_line': 5.5},
    },
    # --- EUROPE (EN 50341) ---
    'EN': {
        132: {'default': 6.0, 'road': 7.0, 'railway': 7.0, 'river': 6.0, 'power_line': 2.0},
        220: {'default': 7.0, 'road': 8.0, 'railway': 8.0, 'river': 7.0, 'power_line': 3.0},
        400: {'default': 8.0, 'road': 9.0, 'railway': 9.0, 'river': 8.0, 'power_line': 4.0},
    },
    # --- GLOBAL FALLBACK (IEC) ---
    'IEC': {
        132: {'default': 6.0, 'road': 7.0, 'railway': 8.0, 'river': 6.0, 'power_line': 3.0},
        220: {'default': 7.0, 'road': 8.0, 'railway': 9.0, 'river': 7.0, 'power_line': 4.0},
        400: {'default': 8.5, 'road': 9.5, 'railway': 10.5, 'river': 8.5, 'power_line': 5.0},
    }
}


class ClearanceResolver:
    """
    Resolves context-aware clearance requirements.
    
    Handles:
    - Voltage snapping to nearest tier
    - Standard code mapping
    - Obstacle-specific clearance requirements
    """
    
    # Voltage tiers available in rules (sorted)
    VOLTAGE_TIERS = [132, 220, 400]
    
    # Mapping from DesignStandard enum to clearance rule code
    STANDARD_TO_RULE_CODE = {
        'IS': 'IS',
        'IEC': 'IEC',
        'EUROCODE': 'EN',
        'ASCE': 'NESC',
    }
    
    def __init__(self, standard_code: str, voltage_kv: float):
        """
        Initialize clearance resolver.
        
        Args:
            standard_code: Standard code ('IS', 'IEC', 'EN', 'NESC')
            voltage_kv: Line voltage in kV
        """
        self.standard_code = standard_code
        self.voltage_kv = voltage_kv
        
        # Snap voltage to nearest tier
        self.snapped_voltage = self._snap_voltage(voltage_kv)
        
        # Get clearance rules for this standard and voltage
        self.current_clearance_rules = self._get_clearance_rules(standard_code, self.snapped_voltage)
    
    def _snap_voltage(self, voltage_kv: float) -> int:
        """
        Snap voltage to next highest tier.
        
        Logic:
        - If voltage <= 132kV, use 132kV rules
        - If 132kV < voltage <= 220kV, use 220kV rules
        - If 220kV < voltage <= 400kV, use 400kV rules
        - If voltage > 400kV, use 400kV rules + 0.01m per kV above 400
        
        Args:
            voltage_kv: Actual voltage in kV
            
        Returns:
            Snapped voltage tier (132, 220, or 400)
        """
        if voltage_kv <= 132:
            return 132
        elif voltage_kv <= 220:
            return 220
        elif voltage_kv <= 400:
            return 400
        else:
            # For voltages > 400kV, use 400kV tier (extra clearance added in get_required_clearance)
            return 400
    
    def _get_clearance_rules(
        self,
        standard_code: str,
        voltage_tier: int
    ) -> Optional[Dict[str, float]]:
        """
        Get clearance rules for standard and voltage tier.
        
        Args:
            standard_code: Standard code ('IS', 'IEC', 'EN', 'NESC')
            voltage_tier: Voltage tier (132, 220, 400)
            
        Returns:
            Dictionary of {obstacle_type: clearance_m} or None if not found
        """
        if standard_code not in GLOBAL_CLEARANCE_RULES:
            # Fallback to IEC if standard not found
            standard_code = 'IEC'
        
        standard_rules = GLOBAL_CLEARANCE_RULES.get(standard_code, {})
        return standard_rules.get(voltage_tier)
    
    def get_required_clearance(
        self,
        distance_along_route: float,
        obstacles: Optional[list] = None
    ) -> float:
        """
        Get required clearance for a specific distance along route.
        
        Considers:
        - Base clearance for voltage/standard
        - Obstacle-specific requirements if distance is within obstacle range
        
        Args:
            distance_along_route: Distance along route in meters
            obstacles: List of obstacle dicts with start_distance_m, end_distance_m, type
            
        Returns:
            Required clearance in meters
        """
        if not self.current_clearance_rules:
            # Fallback to IEC 220kV if rules not found
            return 7.0
        
        # Start with default clearance
        base_req = self.current_clearance_rules.get('default', 7.0)
        
        # Check if distance is within any obstacle
        if obstacles:
            for obstacle in obstacles:
                start_dist = obstacle.get('start_distance_m', 0)
                end_dist = obstacle.get('end_distance_m', 0)
                obstacle_type = obstacle.get('type', 'default')
                
                # Check if distance is within obstacle range
                if start_dist <= distance_along_route <= end_dist:
                    # Map obstacle type to clearance rule key
                    rule_key = self._map_obstacle_type(obstacle_type)
                    
                    # Get obstacle-specific clearance requirement
                    obstacle_req = self.current_clearance_rules.get(rule_key, base_req)
                    
                    # Use maximum of base and obstacle-specific requirement
                    base_req = max(base_req, obstacle_req)
        
        # Add extra clearance for voltages > 400kV
        if self.voltage_kv > 400:
            extra_clearance = (self.voltage_kv - 400) * 0.01  # 0.01m per kV above 400
            base_req += extra_clearance
        
        return base_req
    
    def _map_obstacle_type(self, obstacle_type: str) -> str:
        """
        Map obstacle type to clearance rule key.
        
        Args:
            obstacle_type: Obstacle type from detector ('highway', 'waterway', 'river', etc.)
            
        Returns:
            Rule key ('road', 'railway', 'river', 'power_line', 'default')
        """
        obstacle_lower = obstacle_type.lower()
        
        # Map to rule keys
        if 'highway' in obstacle_lower or 'road' in obstacle_lower:
            return 'road'
        elif 'railway' in obstacle_lower or 'rail' in obstacle_lower:
            return 'railway'
        elif 'river' in obstacle_lower or 'waterway' in obstacle_lower or 'water' in obstacle_lower:
            return 'river'
        elif 'power' in obstacle_lower or 'line' in obstacle_lower:
            return 'power_line'
        else:
            return 'default'
    
    @classmethod
    def from_design_standard(
        cls,
        design_standard: str,
        voltage_kv: float
    ) -> 'ClearanceResolver':
        """
        Create resolver from DesignStandard enum value.
        
        Args:
            design_standard: DesignStandard enum value ('IS', 'IEC', 'EUROCODE', 'ASCE')
            voltage_kv: Line voltage in kV
            
        Returns:
            ClearanceResolver instance
        """
        # Map DesignStandard to rule code
        standard_code = cls.STANDARD_TO_RULE_CODE.get(design_standard, 'IEC')
        return cls(standard_code, voltage_kv)

