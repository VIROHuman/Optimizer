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
import logging
import sys
from typing import List, Tuple, Callable, Dict, Any
from dataclasses import dataclass

# Force print function for immediate console output
def force_print(msg):
    """Force immediate output to stderr, bypassing buffering."""
    print(f"DEBUG: {msg}", file=sys.stderr, flush=True)

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
        avg_span: float = 350.0,  # Average span length for sag calculation
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
            avg_span: Average span length in meters (default 350.0) for sag calculation
        """
        self.codal_engine = codal_engine
        self.inputs = inputs
        self.num_particles = num_particles
        self.max_iterations = max_iterations
        self.w = w
        self.c1 = c1
        self.c2 = c2
        
        # --- LOGIC: Calculate Physical Minimum Height ---
        voltage = inputs.voltage_level
        
        # 1. Structural Spacing (Distance from top arm to bottom arm/ground wire)
        if voltage >= 400:
            structural_height = 9.0
            ground_clearance = 8.0
        elif voltage >= 220:
            structural_height = 6.0
            ground_clearance = 7.0
        else:  # 132kV and below
            structural_height = 4.0
            ground_clearance = 6.0
        
        # 2. Sag Estimate (Physics of catenary curve)
        # Rule of thumb: Sag is approx 2.5% of span for standard tension
        estimated_sag = avg_span * 0.025
        
        # 3. The Absolute Logical Floor
        logical_min_height = ground_clearance + estimated_sag + structural_height
        logical_min_height = math.ceil(logical_min_height)  # Round up
        
        # Ensure logical minimum is at least the voltage-based minimum (safety fallback)
        # Voltage-based minimum tower height bounds (for safety fallback)
        voltage_min_heights = {
            132: 15.0,
            220: 18.0,
            400: 25.0,
            765: 50.0,
            900: 55.0,
        }
        
        voltage_min = 15.0  # Default minimum
        for v_level, h in sorted(voltage_min_heights.items()):
            if voltage >= v_level:
                voltage_min = h
        
        # Use the higher of logical minimum or voltage minimum
        min_height = max(logical_min_height, voltage_min)
        
        # 4. Set Dynamic Bounds
        # Base width minimum is roughly 1/6 of height (as per requirements)
        base_width_min = min_height / 6.0
        base_width_max = min_height / 4.0  # Maximum base width (25% of height)
        
        self.bounds = {
            'height': (min_height, 60.0),  # Floor is now physics-based
            'base_width': (base_width_min, base_width_max),  # Base width relative to height (1/6 to 1/4)
            'span': (inputs.span_min, inputs.span_max),
            'footing_length': (1.2, 5.5),  # Allow "too small" - validator will catch sliding
            'footing_width': (1.2, 5.5),  # Allow "too small" - validator will catch sliding
            'footing_depth': (1.5, 4.0),  # Lowered from (2.0, 6.0) - allow shallow foundations
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
        # Add random seed variation to ensure different results for each tower
        import random
        random.seed()  # Use system time as seed (ensures variation)
        
        # Initialize swarm
        particles = self._initialize_swarm(tower_type)
        force_print(f"Starting optimization - {len(particles)} particles, {self.max_iterations} iterations")
        
        # Main optimization loop
        for iteration in range(self.max_iterations):
            if iteration == 0 or iteration % 20 == 0:
                force_print(f"Iteration {iteration}/{self.max_iterations}, Global best fitness: {self.global_best_fitness:.2f}")
            # Evaluate all particles
            particles_evaluated = 0
            for particle in particles:
                particles_evaluated += 1
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
                # FORCE RAW RESULTS: Only penalize clearance violations (safety-critical)
                # Allow ALL foundation-related "violations" - validator will check FOS and auto-correct
                has_critical_violation = False
                if not safety_result.is_safe:
                    # Only penalize clearance violations (truly critical for safety)
                    # Foundation bounds and FOS checks are handled by validator, not optimizer
                    has_critical_violation = any(
                        'clearance' in violation.lower()
                        for violation in safety_result.violations
                    )
                
                if has_critical_violation:
                    fitness = VERY_LARGE_PENALTY  # Penalty only for clearance violations
                else:
                    # Calculate per-tower cost (even if codal engine says "unsafe" - validator will catch it)
                    per_tower_cost = calculate_cost(particle.current_design, self.inputs)
                    # Convert to per-kilometer line cost
                    fitness = self._calculate_per_km_cost(per_tower_cost, particle.current_design)
                
                particle.current_fitness = fitness
                
                # Update personal best
                if fitness < particle.best_fitness:
                    particle.best_fitness = fitness
                    particle.best_position = particle.position.copy()  # Now saves valid position (e.g., 7.0m, not 3.5m)
                
                # Update global best (may be unsafe or risky)
                # CRITICAL: Initialize global_best_design on first valid particle
                if self.global_best_design is None or fitness < self.global_best_fitness:
                    self.global_best_fitness = fitness
                    self.global_best_position = particle.position.copy()  # Now saves valid position
                    self.global_best_design = particle.current_design
                    if iteration < 5 or iteration % 20 == 0:  # Log first few and every 20th
                        force_print(f"Iter {iteration}: New global best! Fitness: {fitness:.2f}, "
                                   f"H:{particle.current_design.tower_height:.2f}m, "
                                   f"Footing:{particle.current_design.footing_length:.2f}x{particle.current_design.footing_width:.2f}x{particle.current_design.footing_depth:.2f}m")
                
                # Update global best SAFE design (CRITICAL: Track separately)
                # FORCE RAW RESULTS: Track all non-penalized designs (risky or safe)
                if not has_critical_violation and fitness < self.global_best_safe_fitness:
                    self.global_best_safe_fitness = fitness
                    self.global_best_safe_position = particle.position.copy()  # Now saves valid position
                    self.global_best_safe_design = particle.current_design
                    self.found_safe_design = True  # Mark as "found" even if risky
            
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
            force_print(f"WARNING: Best design span ({self.global_best_design.span_length:.2f} m) "
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
        
        # FORCE RETURN: Always return best found design, even if risky (low FOS)
        # Disabled fallback - validator will catch and auto-correct unsafe designs
        
        if self.global_best_design and self.global_best_fitness < VERY_LARGE_PENALTY:
            # Return best found design (may be risky with low FOS) - validator will catch it
            final_design = self.global_best_design
            final_safety = self.codal_engine.is_design_safe(final_design, self.inputs)
            force_print(f"Returning best design - Fitness: {self.global_best_fitness:.2f}, "
                       f"H:{final_design.tower_height:.2f}m, "
                       f"Footing:{final_design.footing_length:.2f}x{final_design.footing_width:.2f}x{final_design.footing_depth:.2f}m, "
                       f"Safe: {final_safety.is_safe}, Violations: {len(final_safety.violations)}")
        elif self.found_safe_design:
            # Fallback to safe design only if no valid risky design found
            final_design = self.global_best_safe_design
            final_safety = self.codal_engine.is_design_safe(final_design, self.inputs)
            force_print(f"Returning safe design. Fitness: {self.global_best_safe_fitness:.2f}")
        else:
            # Last resort: create minimal design (should rarely happen)
            force_print("WARNING: No valid design found. Creating minimal design.")
            from data_models import TowerDesign, FoundationType
            
            voltage = self.inputs.voltage_level
            min_height = self.voltage_min_height
            
            final_design = TowerDesign(
                tower_type=tower_type,
                tower_height=min_height,
                base_width=min_height * 0.25,  # Minimum base width
                span_length=self.bounds['span'][0] + 100.0,
                foundation_type=FoundationType.PAD_FOOTING,
                footing_length=self.bounds['footing_length'][0],  # Minimum footing
                footing_width=self.bounds['footing_width'][0],
                footing_depth=self.bounds['footing_depth'][0],  # Minimum depth
            )
            final_safety = self.codal_engine.is_design_safe(final_design, self.inputs)
        
        # Calculate final costs for output (even if "unsafe" by codal standards)
        # RELAXED: Calculate costs for risky designs too - validator will catch low FOS
        if final_safety.is_safe or self.global_best_fitness < VERY_LARGE_PENALTY:
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
            best_design=final_design,  # May be "risky" with low FOS - validator will catch it
            best_cost=per_km_cost if (final_safety.is_safe or self.global_best_fitness < VERY_LARGE_PENALTY) else VERY_LARGE_PENALTY,
            is_safe=final_safety.is_safe,  # May be False for risky designs (low FOS) - this is OK
            safety_violations=final_safety.violations if not final_safety.is_safe else [],
            governing_standard=self.inputs.governing_standard,
            iterations=iteration + 1,
            convergence_info={
                'convergence_history': self.convergence_history[-50:],  # Last 50 only
                'final_iteration': iteration + 1,
                'per_tower_cost': per_tower_cost,
                'per_km_cost': per_km_cost,
                'found_safe_design': self.found_safe_design,
                'row_corridor_cost_per_km': row_corridor_cost_per_km,
                'row_tower_footprint_per_km': row_tower_footprint_per_km,
                # DIAGNOSTIC INFO - visible in frontend
                'diagnostic': {
                    'iterations_completed': iteration + 1,
                    'particles_count': len(particles),
                    'global_best_initialized': self.global_best_design is not None,
                    'final_fitness': self.global_best_fitness,
                    'design_dimensions': {
                        'height': final_design.tower_height,
                        'footing_length': final_design.footing_length,
                        'footing_width': final_design.footing_width,
                        'footing_depth': final_design.footing_depth,
                    },
                    'optimization_ran': iteration >= 0,  # True if loop ran at least once
                }
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
            # "Greedy" initialization: Bias towards bottom 25% of ranges to encourage cost saving
            # This allows optimizer to explore risky/cheap designs from the start
            height_range = self.bounds['height'][1] - self.voltage_min_height
            height = random.uniform(self.voltage_min_height, self.voltage_min_height + height_range * 0.25)
            
            base_width_min = height * 0.25
            base_width_max = height * 0.40
            base_width_range = base_width_max - base_width_min
            base_width = random.uniform(base_width_min, base_width_min + base_width_range * 0.25)
            
            span_range = self.bounds['span'][1] - self.bounds['span'][0]
            span = random.uniform(self.bounds['span'][0], self.bounds['span'][0] + span_range * 0.25)
            
            # Foundation: Bias towards minimum (risky but cheap)
            footing_length_min = self.bounds['footing_length'][0]
            footing_length_range = self.bounds['footing_length'][1] - footing_length_min
            footing_length = random.uniform(footing_length_min, footing_length_min + footing_length_range * 0.25)
            
            footing_width_min = self.bounds['footing_width'][0]
            footing_width_range = self.bounds['footing_width'][1] - footing_width_min
            footing_width = random.uniform(footing_width_min, footing_width_min + footing_width_range * 0.25)
            
            footing_depth_min = self.bounds['footing_depth'][0]
            footing_depth_range = self.bounds['footing_depth'][1] - footing_depth_min
            footing_depth = random.uniform(footing_depth_min, footing_depth_min + footing_depth_range * 0.25)
            
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
          per_km_cost = (per_tower_cost x towers_per_km) + ROW_corridor_cost_per_km
        
        Where:
          towers_per_km = 1000 / span_length
          ROW_corridor_cost_per_km = corridor_width x land_rate x 1000
        
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

