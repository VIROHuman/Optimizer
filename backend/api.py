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

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.models.request import OptimizationRequest
from backend.models.response import OptimizationResponse
from backend.services.optimizer_service import run_optimization

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


@app.post("/optimize", response_model=OptimizationResponse)
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
            "location": request.location,
            "voltage": request.voltage,
            "terrain": request.terrain,
            "wind": request.wind,
            "soil": request.soil,
            "tower": request.tower,
            "design_for_higher_wind": request.flags.design_for_higher_wind,
            "include_ice_load": request.flags.include_ice_load,
            "conservative_foundation": request.flags.conservative_foundation,
            "high_reliability": False,  # Not in flags, default to False
        }
        
        # Run optimization
        # The service is guaranteed to return a structured response, never raise
        result = run_optimization(input_dict)
        
        # Get codal engine name for display
        from backend.services.optimizer_service import create_codal_engine
        from location_to_code import get_governing_standard
        governing_standard = get_governing_standard(request.location)
        codal_engine = create_codal_engine(governing_standard)
        codal_engine_name = codal_engine.standard_name
        
        # Convert service result to response model format
        # Pass through ALL fields from service to maintain complete output mapping
        design = result["optimized_design"]
        
        cost = None
        if result.get("cost_breakdown"):
            cost = result["cost_breakdown"]
        
        safety = {
            "is_safe": result["safety_status"]["is_safe"],
            "violations": result["safety_status"].get("violations", []),
        }
        
        # Preserve warning structure (dict with type, message, severity) instead of converting to strings
        warnings = result.get("warnings", [])
        # Ensure all warnings are dicts (already converted in service, but defensive check)
        warnings = [
            w if isinstance(w, dict) else {"type": "constructability", "message": str(w)}
            for w in warnings
        ]
        
        advisories = result.get("risk_advisories", [])
        
        response = OptimizationResponse(
            design=design,
            cost=cost,
            safety=safety,
            warnings=warnings,
            advisories=advisories,
            project_context=result.get("project_context"),
            line_level_summary=result.get("line_level_summary"),
            regional_risks=result.get("regional_risks", []),
            reference_data_status=result.get("reference_data_status"),
            design_scenarios_applied=result.get("design_scenarios_applied", []),
            optimization_info=result.get("optimization_info"),
            codal_engine_name=codal_engine_name,
        )
        
        return response
        
    except ValueError as e:
        # Input validation errors (e.g., invalid enum values) - return 400
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected errors - log and return structured error response
        import traceback
        error_detail = str(e)
        print(f"ERROR in API endpoint: {error_detail}")
        print(traceback.format_exc())
        
        # Return error as unsafe design with violation, not HTTP exception
        # This maintains API contract - always returns OptimizationResponse
        error_design = {
            "tower_type": "suspension",
            "tower_height": 40.0,
            "base_width": 10.0,
            "span_length": 350.0,
            "foundation_type": "pad_footing",
            "footing_length": 4.0,
            "footing_width": 4.0,
            "footing_depth": 3.0,
        }
        
        error_safety = {
            "is_safe": False,
            "violations": [f"Backend error: {error_detail}"],
        }
        
        error_response = OptimizationResponse(
            design=error_design,
            cost=None,
            safety=error_safety,
            warnings=[],
            advisories=[],
            project_context=None,
            line_level_summary=None,
            regional_risks=[],
            reference_data_status=None,
            design_scenarios_applied=[],
            optimization_info=None,
            codal_engine_name=None,
        )
        
        return error_response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

