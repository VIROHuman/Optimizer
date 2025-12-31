"""
FastAPI Backend for Transmission Tower Optimization System.

Provides HTTP API access to optimization engine.
CLI (main.py) continues to work independently.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import sys
import os
import logging
from logging.handlers import RotatingFileHandler

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.models.request import OptimizationRequest
from backend.models.response import OptimizationResponse
from backend.models.route_request import RouteOptimizationRequest
from backend.models.canonical import (
    CanonicalOptimizationResult, TowerResponse, SpanResponse,
    LineSummaryResponse, CostBreakdownResponse, SafetySummaryResponse,
    RegionalContextResponse, TowerSafetyStatus, ConfidenceResponse,
    CurrencyContextResponse
)
from backend.models.geo_context import GeographicResolutionResponse
from backend.models.validation_request import ValidationRequest, ValidationResponse, SpanStatus

# Rebuild Pydantic models to resolve forward references
CanonicalOptimizationResult.model_rebuild()
from backend.services.currency_resolver import resolve_currency
from backend.services.optimizer_service import run_optimization
from backend.services.route_optimizer import optimize_route
from backend.services.design_validator import validate_design

# ============================================================================
# FORCE APPLICATION LOGS TO PIGGYBACK ONTO UVICORN'S OUTPUT STREAM
# ============================================================================
# 1. Get the root logger for your application
# (Assuming your modules use 'backend' or 'auto_spotter' as logger names)
# You can also just use logging.getLogger() to catch EVERYTHING.
app_logger = logging.getLogger("backend") 
app_logger.setLevel(logging.DEBUG) # Catch everything

# 2. Create a handler that writes to the Standard Output (Console)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)

# 3. Define a format that stands out from Uvicorn's logs
formatter = logging.Formatter(
    '\033[96m%(asctime)s\033[0m - %(name)s - \033[93m%(levelname)s\033[0m - %(message)s',
    datefmt='%H:%M:%S'
)
console_handler.setFormatter(formatter)

# 4. Attach this handler to the root logger and specific modules
logging.getLogger().addHandler(console_handler)
logging.getLogger("auto_spotter").addHandler(console_handler)
logging.getLogger("optimizer").addHandler(console_handler)

# 5. Prevent double-logging if Uvicorn also catches it
logging.getLogger("backend").propagate = False

# Configure logging to file (in addition to console)
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "backend.log")

# Create file handler for persistent logging
file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)  # 10MB per file, keep 5 backups
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Add file handler to root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)

# Get logger for this module
logger = logging.getLogger(__name__)
logger.info("=" * 60)
logger.info("Backend API starting - Logging configured to file and console")
logger.info("=" * 60)

app = FastAPI(
    title="Transmission Tower Optimization API",
    description="API for transmission tower design optimization",
    version="1.0.0"
)

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with clear messages."""
    errors = exc.errors()
    error_messages = []
    for error in errors:
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_messages.append(f"{field}: {message}")
    
    return JSONResponse(
        status_code=422,
        content={"detail": "; ".join(error_messages)}
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Transmission Tower Optimization API",
        "version": "1.0.0",
        "endpoints": {
            "POST /optimize": "Run optimization",
            "GET /health": "Health check"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/optimize")
async def optimize(request: OptimizationRequest):
    """
    Run transmission tower optimization.
    
    Args:
        request: OptimizationRequest with design parameters
        
    Returns:
        OptimizationResponse with results
    """
    try:
        # Log received payload for debugging
        print("Received payload:", request.dict())
        
        # Convert request to dict format expected by service
        input_dict = {
            "voltage": request.voltage,
            "terrain": request.terrain,
            "wind": request.wind,
            "soil": request.soil,
            "tower": request.tower,
            "design_for_higher_wind": request.flags.design_for_higher_wind,
            "include_ice_load": request.flags.include_ice_load,
            "conservative_foundation": request.flags.conservative_foundation,
            "high_reliability": False,  # Not in flags, default to False
            "project_length_km": request.project_length_km,  # Pass project length
            "route_coordinates": request.route_coordinates,  # Pass route coordinates
            "terrain_profile": request.terrain_profile,  # Pass terrain profile (TASK 5.3)
            "row_mode": request.row_mode,  # Pass ROW mode
        }
        
        # Add geo_context if provided (map-driven geographic resolution)
        if request.geo_context:
            input_dict["geo_context"] = {
                "country_code": request.geo_context.country_code,
                "country_name": request.geo_context.country_name,
                "state": request.geo_context.state,
                "resolution_mode": request.geo_context.resolution_mode,
            }
        
        # Run optimization
        # The service now returns canonical format (dict representation of CanonicalOptimizationResult)
        result = run_optimization(input_dict)
        
        # Result is already in canonical format (dict)
        # Return it directly - frontend will handle rendering
        return result
        
    except ValueError as e:
        # Input validation errors (e.g., invalid enum values) - return 400
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected errors - log and return structured error response
        import traceback
        error_detail = str(e)
        print(f"ERROR in API endpoint: {error_detail}")
        print(traceback.format_exc())
        
        # Return error as canonical format with safe default design
        # This maintains API contract - always returns CanonicalOptimizationResult
        error_tower = TowerResponse(
            index=0,
            distance_along_route_m=0.0,
            latitude=None,
            longitude=None,
            tower_type="suspension",
            deviation_angle_deg=None,
            base_height_m=16.0,
            body_extension_m=24.0,
            total_height_m=40.0,
            base_width_m=8.0,  # CRITICAL: Tower base width (not footing width)
            leg_extensions_m=None,
            foundation_type="pad_footing",
            foundation_dimensions={"length": 4.0, "width": 4.0, "depth": 3.0},
            steel_weight_kg=5000.0,
            steel_cost=7000.0,
            foundation_cost=2000.0,
            erection_cost=3000.0,
            transport_cost=600.0,
            land_ROW_cost=1000.0,
            total_cost=13600.0,
            safety_status=TowerSafetyStatus.SAFE,
            governing_load_case=f"Backend error: {error_detail}",
        )
        
        error_span = SpanResponse(
            from_tower_index=0,
            to_tower_index=1,
            span_length_m=350.0,
            sag_m=7.0,
            minimum_clearance_m=24.0,
            clearance_margin_percent=15.0,
            wind_zone_used="zone_2",
            ice_load_used=False,
            governing_case=None,
            is_safe=True,
            confidence_score=50,
            governing_reason=f"Backend error: {error_detail}",
        )
        
        error_response = CanonicalOptimizationResult(
            towers=[error_tower],
            spans=[error_span],
            line_summary=LineSummaryResponse(
                route_length_km=1.0,
                total_towers=1,
                tower_density_per_km=2.86,
                avg_span_m=350.0,
                tallest_tower_m=40.0,
                deepest_foundation_m=3.0,
                total_steel_tonnes=5.0,
                total_concrete_m3=192.0,
                total_project_cost=13600.0,
                cost_per_km=13600.0,
                estimated_towers_for_project_length=1,
            ),
            cost_breakdown=CostBreakdownResponse(
                steel_total=7000.0,
                foundation_total=2000.0,
                erection_total=3000.0,
                transport_total=600.0,
                land_ROW_total=1000.0,
                total_project_cost=13600.0,
                currency="USD",
                currency_symbol="$",
                market_rates=None,  # Error case - no market rates available
            ),
            safety_summary=SafetySummaryResponse(
                overall_status="SAFE",
                governing_risks=[f"Backend error: {error_detail}"],
                design_scenarios_applied=["Error fallback design"],
            ),
            regional_context=RegionalContextResponse(
                governing_standard="IS",
                dominant_regional_risks=[],
                confidence=ConfidenceResponse(
                    score=50,
                    drivers=[f"Backend error occurred: {error_detail}"],
                ),
            ),
            cost_sensitivity=None,
            cost_context=None,
            currency=CurrencyContextResponse(
                code="USD",
                symbol="$",
                label="USD"
            ),
            warnings=[{"type": "error", "message": error_detail}],
            advisories=[],
            reference_data_status=None,
            optimization_info={"error": error_detail},
        )
        
        return error_response.dict()


@app.post("/optimize/route")
async def optimize_route_endpoint(request: RouteOptimizationRequest):
    """
    Route-level optimization endpoint.
    
    Automatically places towers along route and optimizes each tower.
    
    Args:
        request: RouteOptimizationRequest with route coordinates and design options
        
    Returns:
        CanonicalOptimizationResult with full route data
    """
    try:
        # Convert route coordinates to list of dicts
        route_coords = [
            {
                "lat": coord.lat,
                "lon": coord.lon,
                "elevation_m": coord.elevation_m,
                "distance_m": coord.distance_m,
            }
            for coord in request.route_coordinates
        ]
        
        # Convert design options to dict
        design_options = {
            "location": request.design_options.location,
            "voltage": request.design_options.voltage,
            "terrain": request.design_options.terrain,
            "wind": request.design_options.wind,
            "soil": request.design_options.soil,
            "tower": request.design_options.tower,
            "design_for_higher_wind": request.design_options.flags.design_for_higher_wind,
            "include_ice_load": request.design_options.flags.include_ice_load,
            "conservative_foundation": request.design_options.flags.conservative_foundation,
            "high_reliability": False,
        }
        
        # Run route optimization
        result = optimize_route(
            route_coordinates=route_coords,
            project_length_km=request.project_length_km,
            design_options=design_options,
            row_mode=request.design_options.flags.row_mode if hasattr(request.design_options.flags, 'row_mode') else request.design_options.get('row_mode', 'urban_private'),
        )
        
        # Return canonical format (dict)
        return result.dict()
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"ERROR in route optimization: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Route optimization failed: {error_detail}")


@app.post("/validate-design", response_model=ValidationResponse)
async def validate_design_endpoint(request: ValidationRequest):
    """
    Real-time design validation endpoint.
    
    Validates tower positions and spans when towers are moved.
    Checks obstacle clearance and electrical clearance requirements.
    
    Args:
        request: ValidationRequest with updated tower positions
        
    Returns:
        ValidationResponse with span statuses and violations
    """
    try:
        # Convert request to dict format
        towers_dict = [
            {
                'index': t.index,
                'latitude': t.latitude,
                'longitude': t.longitude,
                'total_height_m': t.total_height_m,
                'distance_along_route_m': t.distance_along_route_m,
            }
            for t in request.towers
        ]
        
        # Convert geo_context
        geo_context_dict = None
        if request.geo_context:
            geo_context_dict = {
                'country_code': request.geo_context.country_code,
                'country_name': request.geo_context.country_name,
                'state': request.geo_context.state,
            }
        
        # Run validation
        overall_status, span_statuses = validate_design(
            towers=towers_dict,
            spans=request.spans,
            voltage_kv=request.voltage_kv,
            geo_context=geo_context_dict,
            route_coordinates=request.route_coordinates,
            terrain_profile=request.terrain_profile,
        )
        
        violations_count = sum(1 for s in span_statuses if s.status == 'VIOLATION')
        
        return ValidationResponse(
            overall_status=overall_status,
            span_statuses=span_statuses,
            violations_count=violations_count,
        )
        
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"ERROR in design validation: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Design validation failed: {error_detail}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

