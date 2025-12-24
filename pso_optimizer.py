"""
Particle Swarm Optimization (PSO) Module.

Manual implementation of PSO for transmission tower design optimization.

═══════════════════════════════════════════════════════════════════════════
CORE CONTRACT (NON-NEGOTIABLE):
═══════════════════════════════════════════════════════════════════════════

This optimizer MUST always return the cheapest SAFE design.

- Explores ONLY feasible designs (bounds enforced during search)
- NEVER interprets engineering codes (delegates to codal engine)
- NEVER overrides safety (penalty-based rejection for unsafe candidates)
- ALWAYS tracks best safe design separately
- FALLBACK: If no safe design found, returns conservative safe design

The optimizer is code-agnostic and relies entirely on the codal engine
for safety validation. Cost minimization is the objective, safety is
a hard constraint enforced via penalty.
═══════════════════════════════════════════════════════════════════════════
"""

import random
import math
from typing import List, Tuple, Callable, Dict, Any
from dataclasses import dataclass

from data_models import (
    TowerDesign, OptimizationInputs, DesignStandard,
    TowerType, FoundationType, SafetyCheckResult, OptimizationResult
)
from codal_engine.base import CodalEngine
from cost_engine import calculate_cost


# Penalty for unsafe designs (must be larger than any realistic cost)
VERY_LARGE_PENALTY = 1e10


def get_base_width_ratio_for_tower_type(tower_type: TowerType) -> float:
    """
    Get minimum base width to height ratio for a given tower type.
    
    Different tower types require different base width ratios based on their
    structural requirements:
    - Suspension towers: least critical, minimum ratio
    - Angle towers: moderate loads, slightly higher ratio
    - Tension towers: higher loads, higher ratio
    - Dead-end towers: highest loads, maximum ratio
    
    Args:
        tower_type: TowerType enum value
        
    Returns:
        Minimum base width ratio (base_width / tower_height)
    """
    ratios = {
        TowerType.SUSPENSION: 0.25,  # Least critical, minimum ratio
        TowerType.ANGLE: 0.28,       # Moderate loads
        TowerType.TENSION: 0.32,     # Higher loads
        TowerType.DEAD_END: 0.35,    # Highest loads, most critical
    }
    return ratios.get(tower_type, 0.25)  # Default to suspension ratio if unknown


@dataclass(frozen=False)  # Must be mutable for PSO updates
class Particle:
    """
    Represents a particle in the PSO swarm.
    
    Each particle has:
    - Position (design parameters)
    - Velocity (search direction)
    - Best known position (personal best)
    - Best known fitness (cost)
    """
    position: List[float]  # Design parameters as continuous values
    velocity: List[float]
    best_position: List[float]
    best_fitness: float
    current_design: TowerDesign  # Decoded design
    current_fitness: float


class PSOOptimizer:
    """
    Particle Swarm Optimization engine for transmission tower design.
    
    This optimizer:
    - Explores design space using PSO algorithm
    - Uses codal engine to validate safety
    - Uses cost engine to evaluate fitness
    - Applies penalty to unsafe designs
    """
    
    def __init__(
        self,
        codal_engine: CodalEngine,
        inputs: OptimizationInputs,
        num_particles: int = 30,
        max_iterations: int = 100,
        w: float = 0.7,  # Inertia weight
        c1: float = 1.5,  # Cognitive coefficient
        c2: float = 1.5,  # Social coefficient
    ):
        """
        Initialize PSO optimizer.
        
        Args:
            codal_engine: CodalEngine instance for safety checks
            inputs: OptimizationInputs with project context
            num_particles: Number of particles in swarm
            max_iterations: Maximum iterations
            w: Inertia weight (0.4-0.9 typical)
            c1: Cognitive coefficient (1.5-2.0 typical)
            c2: Social coefficient (1.5-2.0 typical)
        """
        self.codal_engine = codal_engine
        self.inputs = inputs
        self.num_particles = num_particles
        self.max_iterations = max_iterations
        self.w = w
        self.c1 = c1
        self.c2 = c2
        
        # Voltage-based minimum tower height bounds
        voltage_min_heights = {
            132: 25.0,
            220: 30.0,
            400: 40.0,
            765: 50.0,
            900: 55.0,
        }
        
        # Find minimum height for voltage level
        voltage = inputs.voltage_level
        min_height = 25.0  # Default minimum
        for v_level, h in sorted(voltage_min_heights.items()):
            if voltage >= v_level:
                min_height = h
        
        # Decision variable bounds
        self.bounds = {
            'height': (min_height, 60.0),
            'base_width': (0.0, 0.0),  # Will be set relative to height
            'span': (inputs.span_min, inputs.span_max),
            'footing_length': (3.0, 8.0),
            'footing_width': (3.0, 8.0),
            'footing_depth': (2.0, 6.0),
        }
        
        # Store voltage minimum for clamping
        self.voltage_min_height = min_height
        
        # Global best (may be unsafe)
        self.global_best_position: List[float] = []
        self.global_best_fitness: float = float('inf')
        self.global_best_design: TowerDesign = None
        
        # Global best SAFE design (CRITICAL: Always track best safe design)
        self.global_best_safe_position: List[float] = []
        self.global_best_safe_fitness: float = float('inf')
        self.global_best_safe_design: TowerDesign = None
        self.found_safe_design: bool = False
        
        # Convergence tracking
        self.convergence_history: List[float] = []
    
    def optimize(
        self,
        tower_type: TowerType = TowerType.SUSPENSION
    ) -> OptimizationResult:
        """
        Run PSO optimization.
        
        Args:
            tower_type: Type of tower to optimize
            
        Returns:
            OptimizationResult with best design and metadata
        """
        # Initialize swarm
        particles = self._initialize_swarm(tower_type)
        
        # Main optimization loop
        for iteration in range(self.max_iterations):
            # Evaluate all particles
            for particle in particles:
                # CRITICAL FIX: Update position vector to match decoded design BEFORE saving best positions
                # This ensures that if base_width was clamped (e.g., 3.5m -> 7.0m), the position vector reflects the actual design
                # Otherwise, best_position will save invalid values that pull other particles toward low base_width
                particle.position[0] = particle.current_design.tower_height
                particle.position[1] = particle.current_design.base_width  # CRITICAL: Use decoded base_width, not raw position
                particle.position[2] = particle.current_design.span_length
                particle.position[3] = particle.current_design.footing_length
                particle.position[4] = particle.current_design.footing_width
                particle.position[5] = particle.current_design.footing_depth
                
                # Check safety
                safety_result = self.codal_engine.is_design_safe(
                    particle.current_design,
                    self.inputs
                )
                
                # Calculate fitness (per-kilometer line cost)
                if safety_result.is_safe:
                    # Calculate per-tower cost
                    per_tower_cost = calculate_cost(particle.current_design, self.inputs)
                    # Convert to per-kilometer line cost
                    fitness = self._calculate_per_km_cost(per_tower_cost, particle.current_design)
                else:
                    fitness = VERY_LARGE_PENALTY  # Penalty for unsafe design
                
                particle.current_fitness = fitness
                
                # Update personal best
                if fitness < particle.best_fitness:
                    particle.best_fitness = fitness
                    particle.best_position = particle.position.copy()  # Now saves valid position (e.g., 7.0m, not 3.5m)
                
                # Update global best (may be unsafe)
                if fitness < self.global_best_fitness:
                    self.global_best_fitness = fitness
                    self.global_best_position = particle.position.copy()  # Now saves valid position
                    self.global_best_design = particle.current_design
                
                # Update global best SAFE design (CRITICAL: Track separately)
                if safety_result.is_safe and fitness < self.global_best_safe_fitness:
                    self.global_best_safe_fitness = fitness
                    self.global_best_safe_position = particle.position.copy()  # Now saves valid position
                    self.global_best_safe_design = particle.current_design
                    self.found_safe_design = True
            
            # Track convergence
            self.convergence_history.append(self.global_best_fitness)
            
            # Update velocities and positions
            for particle in particles:
                self._update_particle(particle)
            
            # Early stopping if converged
            if iteration > 20:
                recent_improvement = (
                    self.convergence_history[-20] - self.convergence_history[-1]
                )
                # Early stopping threshold adjusted for per-km cost (typically $10k-$50k/km)
                if recent_improvement < 1000.0:  # Less than $1000/km improvement in last 20 iterations
                    break
        
        # Defensive check: Ensure best design is within bounds
        # This should never trigger if clamping works correctly, but serves as safety net
        if (self.global_best_design.span_length < self.bounds['span'][0] or 
            self.global_best_design.span_length > self.bounds['span'][1]):
            # Log warning and clamp (should never happen)
            print(f"WARNING: Best design span ({self.global_best_design.span_length:.2f} m) "
                  f"outside bounds [{self.bounds['span'][0]}, {self.bounds['span'][1]}]. Clamping.")
            clamped_span = max(self.bounds['span'][0], min(self.bounds['span'][1], self.global_best_design.span_length))
            # Create new design with clamped span
            from data_models import TowerDesign
            self.global_best_design = TowerDesign(
                tower_type=self.global_best_design.tower_type,
                tower_height=self.global_best_design.tower_height,
                base_width=self.global_best_design.base_width,
                span_length=clamped_span,
                foundation_type=self.global_best_design.foundation_type,
                footing_length=self.global_best_design.footing_length,
                footing_width=self.global_best_design.footing_width,
                footing_depth=self.global_best_design.footing_depth,
            )
        
        # CRITICAL: Always use best SAFE design if found, otherwise create conservative safe design
        if self.found_safe_design:
            # Use best safe design found during optimization
            final_design = self.global_best_safe_design
            final_safety = self.codal_engine.is_design_safe(final_design, self.inputs)
        else:
            # No safe design found - create conservative safe design
            # This should rarely happen, but ensures we NEVER return unsafe final design
            print("WARNING: No safe design found during optimization. Using conservative safe design.")
            from data_models import TowerDesign, FoundationType
            
            # Conservative safe design: taller tower, larger base, shorter span
            voltage = self.inputs.voltage_level
            min_height = 40.0
            if voltage >= 765:
                min_height = 50.0
            elif voltage >= 400:
                min_height = 45.0
            
            final_design = TowerDesign(
                tower_type=self.global_best_design.tower_type if self.global_best_design else tower_type,
                tower_height=min_height,
                base_width=max(12.0, min_height * 0.3),  # Conservative base width
                span_length=self.bounds['span'][0] + 50.0,  # Shorter span (safer)
                foundation_type=FoundationType.PAD_FOOTING,
                footing_length=5.0,  # Larger footing
                footing_width=5.0,
                footing_depth=4.0,  # Deeper foundation
            )
            final_safety = self.codal_engine.is_design_safe(final_design, self.inputs)
            # If still unsafe, log error (should never happen with conservative values)
            if not final_safety.is_safe:
                print(f"ERROR: Conservative design still unsafe. Violations: {final_safety.violations}")
                # Force safe by using even more conservative values
                final_design = TowerDesign(
                    tower_type=final_design.tower_type,
                    tower_height=min_height + 5.0,
                    base_width=min_height * 0.35,
                    span_length=self.bounds['span'][0],
                    foundation_type=FoundationType.PAD_FOOTING,
                    footing_length=6.0,
                    footing_width=6.0,
                    footing_depth=5.0,
                )
                final_safety = self.codal_engine.is_design_safe(final_design, self.inputs)
        
        # Calculate final costs for output
        if final_safety.is_safe:
            per_tower_cost = calculate_cost(final_design, self.inputs)
            per_km_cost = self._calculate_per_km_cost(per_tower_cost, final_design)
            
            # Calculate ROW costs for output
            from cost_engine import calculate_row_corridor_cost_per_km, _calculate_land_cost
            row_corridor_cost_per_km = calculate_row_corridor_cost_per_km(self.inputs)
            tower_footprint_land_cost = _calculate_land_cost(final_design, self.inputs)
            towers_per_km = 1000.0 / final_design.span_length
            row_tower_footprint_per_km = tower_footprint_land_cost * towers_per_km
        else:
            per_tower_cost = VERY_LARGE_PENALTY
            per_km_cost = VERY_LARGE_PENALTY
            row_corridor_cost_per_km = 0.0
            row_tower_footprint_per_km = 0.0
        
        return OptimizationResult(
            best_design=final_design,  # Always use safe design (or conservative safe design)
            best_cost=per_km_cost if final_safety.is_safe else VERY_LARGE_PENALTY,
            is_safe=final_safety.is_safe,  # Should always be True now
            safety_violations=final_safety.violations if not final_safety.is_safe else [],
            governing_standard=self.inputs.governing_standard,
            iterations=iteration + 1,
            convergence_info={
                'convergence_history': self.convergence_history,
                'final_iteration': iteration + 1,
                'per_tower_cost': per_tower_cost,
                'per_km_cost': per_km_cost,
                'found_safe_design': self.found_safe_design,  # Track if safe design was found
                'row_corridor_cost_per_km': row_corridor_cost_per_km,
                'row_tower_footprint_per_km': row_tower_footprint_per_km,
            }
        )
    
    def _initialize_swarm(self, tower_type: TowerType) -> List[Particle]:
        """
        Initialize particle swarm with random positions.
        
        Args:
            tower_type: Type of tower
            
        Returns:
            List of initialized particles
        """
        particles = []
        
        for _ in range(self.num_particles):
            # Random position within bounds
            # Enforce voltage-based minimum height
            height = random.uniform(self.voltage_min_height, self.bounds['height'][1])
            base_width_min = height * 0.25
            base_width_max = height * 0.40
            base_width = random.uniform(base_width_min, base_width_max)
            span = random.uniform(*self.bounds['span'])
            footing_length = random.uniform(*self.bounds['footing_length'])
            footing_width = random.uniform(*self.bounds['footing_width'])
            footing_depth = random.uniform(*self.bounds['footing_depth'])
            
            position = [
                height,
                base_width,
                span,
                footing_length,
                footing_width,
                footing_depth,
            ]
            
            # Random velocity
            velocity = [
                random.uniform(-1, 1) * (self.bounds['height'][1] - self.bounds['height'][0]) * 0.1,
                random.uniform(-1, 1) * height * 0.1,
                random.uniform(-1, 1) * (self.bounds['span'][1] - self.bounds['span'][0]) * 0.1,
                random.uniform(-1, 1) * (self.bounds['footing_length'][1] - self.bounds['footing_length'][0]) * 0.1,
                random.uniform(-1, 1) * (self.bounds['footing_width'][1] - self.bounds['footing_width'][0]) * 0.1,
                random.uniform(-1, 1) * (self.bounds['footing_depth'][1] - self.bounds['footing_depth'][0]) * 0.1,
            ]
            
            # Decode to design
            design = self._decode_position(position, tower_type)
            
            # Initialize particle
            particle = Particle(
                position=position,
                velocity=velocity,
                best_position=position.copy(),
                best_fitness=float('inf'),
                current_design=design,
                current_fitness=float('inf'),
            )
            particles.append(particle)
        
        return particles
    
    def _decode_position(
        self,
        position: List[float],
        tower_type: TowerType
    ) -> TowerDesign:
        """
        Decode continuous position vector to TowerDesign.
        
        Args:
            position: [height, base_width, span, footing_length, footing_width, footing_depth]
            tower_type: Type of tower
            
        Returns:
            TowerDesign instance
        """
        height, base_width, span, footing_length, footing_width, footing_depth = position
        
        # Clamp to bounds - CRITICAL: This ensures all designs are within valid ranges
        # The optimizer MUST enforce bounds here, not rely on post-validation
        # Enforce voltage-based minimum height
        height = max(self.voltage_min_height, min(self.bounds['height'][1], height))
        base_width_min = height * 0.25
        base_width_max = height * 0.40
        base_width = max(base_width_min, min(base_width_max, base_width))
        
        # CRITICAL: Span must be clamped to bounds (250-450 m by default)
        # This is enforced here, not in post-validation
        span = max(self.bounds['span'][0], min(self.bounds['span'][1], span))
        
        footing_length = max(self.bounds['footing_length'][0], min(self.bounds['footing_length'][1], footing_length))
        footing_width = max(self.bounds['footing_width'][0], min(self.bounds['footing_width'][1], footing_width))
        footing_depth = max(self.bounds['footing_depth'][0], min(self.bounds['footing_depth'][1], footing_depth))
        
        # Choose foundation type (simplified: use pad footing)
        foundation_type = FoundationType.PAD_FOOTING
        
        return TowerDesign(
            tower_type=tower_type,
            tower_height=height,
            base_width=base_width,
            span_length=span,
            foundation_type=foundation_type,
            footing_length=footing_length,
            footing_width=footing_width,
            footing_depth=footing_depth,
        )
    
    def _update_particle(self, particle: Particle):
        """
        Update particle velocity and position using PSO equations.
        
        Args:
            particle: Particle to update
        """
        # Update velocity
        for i in range(len(particle.position)):
            r1 = random.random()
            r2 = random.random()
            
            # PSO velocity update equation
            cognitive = self.c1 * r1 * (particle.best_position[i] - particle.position[i])
            social = self.c2 * r2 * (self.global_best_position[i] - particle.position[i])
            particle.velocity[i] = (
                self.w * particle.velocity[i] + cognitive + social
            )
        
        # Update position
        for i in range(len(particle.position)):
            particle.position[i] += particle.velocity[i]
        
        # Decode new position to design
        particle.current_design = self._decode_position(
            particle.position,
            particle.current_design.tower_type
        )
        
        # CRITICAL FIX: Update position vector to match decoded design
        # This ensures that if base_width was clamped (e.g., 3.5m -> 7.0m), the position vector reflects the actual design
        # This prevents the optimizer from being pulled toward invalid low base_width values
        particle.position[0] = particle.current_design.tower_height
        particle.position[1] = particle.current_design.base_width  # CRITICAL: Use decoded base_width, not raw position
        particle.position[2] = particle.current_design.span_length
        particle.position[3] = particle.current_design.footing_length
        particle.position[4] = particle.current_design.footing_width
        particle.position[5] = particle.current_design.footing_depth
    
    def _calculate_per_km_cost(
        self,
        per_tower_cost: float,
        design: TowerDesign
    ) -> float:
        """
        Calculate per-kilometer line cost from per-tower cost.
        
        This is the optimization objective function.
        
        Formula:
          per_km_cost = (per_tower_cost × towers_per_km) + ROW_corridor_cost_per_km
        
        Where:
          towers_per_km = 1000 / span_length
          ROW_corridor_cost_per_km = corridor_width × land_rate × 1000
        
        Note: per_tower_cost includes tower footprint land cost.
        Corridor ROW cost is added separately at line level.
        
        Args:
            per_tower_cost: Cost per single tower (USD), includes tower footprint land cost
            design: TowerDesign with span length
            
        Returns:
            Cost per kilometer of transmission line (USD/km)
        """
        from cost_engine import calculate_row_corridor_cost_per_km
        
        # Calculate towers per kilometer
        towers_per_km = 1000.0 / design.span_length
        
        # Per-tower costs per kilometer
        tower_costs_per_km = per_tower_cost * towers_per_km
        
        # ROW corridor cost per kilometer (DOMINANT ROW component)
        row_corridor_cost_per_km = calculate_row_corridor_cost_per_km(self.inputs)
        
        # Total per-kilometer line cost
        per_km_cost = tower_costs_per_km + row_corridor_cost_per_km
        
        return per_km_cost

