"""
FastAPI Backend for Transmission Tower Optimization System.

Provides HTTP API access to optimization engine.
CLI (main.py) continues to work independently.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

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


class OptimizationRequest(BaseModel):
    """Request model for optimization endpoint."""
    location: str
    voltage: int
    terrain: str
    wind: str
    soil: str
    tower: str
    design_for_higher_wind: bool = False
    include_ice_load: bool = False
    conservative_foundation: bool = False
    high_reliability: bool = False
    span_min: Optional[float] = 200.0
    span_max: Optional[float] = 600.0
    particles: Optional[int] = 30
    iterations: Optional[int] = 100


class OptimizationResponse(BaseModel):
    """Response model for optimization endpoint."""
    project_context: Dict[str, Any]
    optimized_design: Dict[str, Any]
    cost_breakdown: Optional[Dict[str, Any]] = None
    line_level_summary: Optional[Dict[str, Any]] = None
    safety_status: Dict[str, Any]
    warnings: list = []
    regional_risks: list = []
    risk_advisories: list = []
    reference_data_status: Dict[str, str]
    design_scenarios_applied: list
    optimization_info: Dict[str, Any]


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
        # Convert request to dict
        input_dict = request.dict()
        
        # Run optimization
        result = run_optimization(input_dict)
        
        return OptimizationResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

