# Transmission Tower Optimization System

A full-stack engineering application for optimizing transmission tower designs with physics-based calculations, PSO optimization, codal compliance checks, and cost estimation.

## 📖 Setup Guides

- **🚀 Quick Start**: See [QUICK_START.md](QUICK_START.md) for 5-minute setup
- **📚 Complete Setup Guide**: See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions including:
  - Step-by-step local setup
  - API keys configuration
  - Free online hosting options
  - Troubleshooting

## Architecture

This is a **monorepo** with two strictly separated projects:

- `/backend` → Python (FastAPI)
- `/frontend` → Next.js + Tailwind CSS v3

They communicate **ONLY** via HTTP APIs. No shared files, no mixed dependencies.

## Prerequisites

- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **Backend dependencies**: FastAPI, Pydantic, Uvicorn
- **Frontend dependencies**: Next.js, React, Tailwind CSS v3

## Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install Python dependencies (if not already installed):
   ```bash
   pip install fastapi uvicorn pydantic
   ```

3. Ensure all project dependencies are available. The backend imports from the parent directory, so make sure you're running from the project root or have the Python path configured correctly.

4. Run the FastAPI server:
   
   **From the project root directory:**
   ```bash
   uvicorn backend.api:app --reload
   ```
   
   **OR from the backend directory:**
   ```bash
   cd backend
   uvicorn api:app --reload
   ```

   The API will be available at `http://localhost:8000`

   - API Documentation: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/health`

## Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

   **Note**: This will install Tailwind CSS v3. If you see Tailwind v4 dependencies, run:
   ```bash
   npm install tailwindcss@^3.4.1 autoprefixer@^10.4.20 --save-dev
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:3000`

## Running Both Services

### Option 1: Two Terminal Windows

**Terminal 1 (Backend):**
```bash
# From project root:
uvicorn backend.api:app --reload

# OR from backend directory:
cd backend
uvicorn api:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

### Option 2: Background Processes

**Backend (background):**
```bash
# From project root:
uvicorn backend.api:app --reload &

# OR from backend directory:
cd backend
uvicorn api:app --reload &
```

**Frontend:**
```bash
cd frontend
npm run dev
```

## API Endpoint

### POST `/optimize`

**Request Body:**
```json
{
  "location": "india",
  "voltage": 400,
  "terrain": "flat",
  "wind": "zone_2",
  "soil": "medium",
  "tower": "suspension",
  "flags": {
    "design_for_higher_wind": false,
    "include_ice_load": false,
    "conservative_foundation": false
  }
}
```

**Response:**
```json
{
  "design": {
    "tower_type": "suspension",
    "tower_height": 45.5,
    "base_width": 12.8,
    "span_length": 400.0,
    "foundation_type": "pad_footing",
    "footing_length": 4.5,
    "footing_width": 4.5,
    "footing_depth": 3.2
  },
  "cost": {
    "steel_cost": 485000,
    "foundation_cost": 245000,
    "erection_cost": 125000,
    "land_cost": 50000,
    "total_cost": 905000,
    "currency": "USD",
    "currency_symbol": "$"
  },
  "safety": {
    "is_safe": true,
    "violations": []
  },
  "warnings": [],
  "advisories": []
}
```

## Project Structure

```
## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND LAYER                                │
│                         (Next.js 16 + React 19)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │ Landing Page │  │  Form Input  │  │   Results    │                   │
│  │  Component   │→ │  Component   │→ │  Component   │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
│         │                  │                  │                         │
│         │                  │                  │                         │
│         └──────────────────┴──────────────────┘                         │
│                            │                                            │
│                    ┌───────▼───────┐                                    │
│                    │   API Client  │                                    │
│                    │  (lib/api.ts) │                                    │
│                    └───────┬───────┘                                    │
│                            │                                            │
│                    HTTP POST/GET                                        │
└────────────────────────────┼────────────────────────────────────────────┘
                             │
                             │ Port 8000
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│                        BACKEND LAYER                                    │
│                    (FastAPI + Python 3.12)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    API ROUTER (api.py)                           │   │
│  │  ┌──────────┐  ┌────────────┐  ┌──────────────┐  ┌──────────────┐│   │
│  │  │   GET /  │  │ GET /health│  │POST /optimize│  │POST /validate││   │ 
│  │  └──────────┘  └────────────┘  └──────────────┘  └──────────────┘│   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                            │                                            │
│                            ▼                                            │
│  ┌───────────────────────────────────────────────────────────────┐      │
│  │              SERVICE LAYER (backend/services/)                │      │
│  │                                                               │      │
│  │  ┌─────────────────────────────────────────────────────┐      │      │
│  │  │         optimizer_service.py                        │      │      │
│  │  │  • Parses input parameters                          │      │      │
│  │  │  • Routes to single-tower OR route optimization     │      │      │
│  │  │  • Returns canonical format                         │      │      │
│  │  └─────────────────────────────────────────────────────┘      │      │
│  │                            │                                  │      │
│  │                            ▼                                  │      │
│  │  ┌──────────────────────────────────────────────────────┐     │      │
│  │  │         route_optimizer.py                           │     │      │
│  │  │  • Orchestrates full route optimization              │     │      │
│  │  │  • Calls SectionBasedPlacer for tower placement      │     │      │
│  │  │  • Calls PSO optimizer for each tower                │     │      │
│  │  │  • Aggregates results                                │     │      │
│  │  └──────────────────────────────────────────────────────┘     │      │
│  │                            │                                  │      │
│  │                            ▼                                  │      │
│  │  ┌─────────────────────────────────────────────────────┐      │      │
│  │  │      section_based_placer.py                        │      │      │
│  │  │  • Phase 1: Corner Merging (< 50m segments)         │      │      │
│  │  │  • Phase 2: Define Sections                         │      │      │
│  │  │  • Phase 3: Optimize Spans (with slack logic)       │      │      │
│  │  │  • Phase 4: Precise Placement (vector math)         │      │      │
│  │  │  • Integrates ObstacleDetector for smart nudging    │      │      │
│  │  └─────────────────────────────────────────────────────┘      │      │
│  │                            │                                  │      │
│  │                            ▼                                  │      │
│  │  ┌─────────────────────────────────────────────────────┐      │      │
│  │  │         obstacle_detector.py                        │      │      │
│  │  │  • Queries OSM Overpass API (rivers, roads, etc.)   │      │      │
│  │  │  • Analyzes terrain slopes (> 30% = forbidden)      │      │      │
│  │  │  • Creates ForbiddenZone objects                    │      │      │
│  │  │  • get_safe_spot() - nudges towers away from zones  │      │      │
│  │  └─────────────────────────────────────────────────────┘      │      │
│  │                            │                                  │      │
│  │                            ▼                                  │      │
│  │  ┌─────────────────────────────────────────────────────┐      │      │
│  │  │         pso_optimizer.py                            │      │      │
│  │  │  • Particle Swarm Optimization algorithm            │      │      │
│  │  │  • Explores design space (height, width, span)      │      │      │
│  │  │  • Calls CodalEngine for safety validation          │      │      │
│  │  │  • Calls CostEngine for cost calculation            │      │      │
│  │  │  • Returns cheapest SAFE design                     │      │      │
│  │  └─────────────────────────────────────────────────────┘      │      │
│  │                            │                                  │      │
│  │                            ▼                                  │      │
│  │  ┌─────────────────────────────────────────────────────┐      │      │
│  │  │         codal_engine/ (IS, IEC, Eurocode, ASCE)     │      │      │
│  │  │  • Implements design standard-specific rules        │      │      │
│  │  │  • Checks electrical clearance                      │      │      │
│  │  │  • Validates structural safety                      │      │      │
│  │  │  • Uses ClearanceResolver for voltage-aware rules   │      │      │
│  │  └─────────────────────────────────────────────────────┘      │      │
│  │                            │                                  │      │
│  │                            ▼                                  │      │
│  │  ┌──────────────────────────────────────────────────────┐     │      │
│  │  │         cost_engine.py                               │     │      │
│  │  │  • Reads market_rates.py for regional costs          │     │      │
│  │  │  • Calculates steel, foundation, erection costs      │     │      │
│  │  │  • Applies labor and logistics factors               │     │      │
│  │  │  • Returns cost breakdown with market rates          │     │      │
│  │  └──────────────────────────────────────────────────────┘     │      │
│  │                            │                                  │      │
│  │                            ▼                                  │      │
│  │  ┌──────────────────────────────────────────────────────┐     │      │
│  │  │         canonical_converter.py                       │     │      │
│  │  │  • Converts OptimizationResult to canonical format   │     │      │
│  │  │  • Adds line summary, cost breakdown, safety         │     │      │
│  │  │  • Includes regional context, currency               │     │      │
│  │  └──────────────────────────────────────────────────────┘     │      │
│  │                                                               │      │
│  │  Supporting Services:                                         │      │
│  │  • location_deriver.py - Reverse geocoding, country detection │      │
│  │  • standard_resolver.py - Design standard resolution          │      │
│  │  • clearance_rules.py - Voltage-aware clearance rules         │      │
│  │  • currency_resolver.py - Currency conversion (USD/INR)       │      │
│  │  • tower_type_classifier.py - Classifies tower types          │      │
│  │  • design_validator.py - Post-optimization validation         │      │
│  └───────────────────────────────────────────────────────────────┘      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Important Notes

1. **Strict Separation**: Frontend and backend are completely independent. They only communicate via HTTP JSON.

2. **Tailwind CSS v3**: The frontend uses **Tailwind CSS v3 ONLY**. No v4 syntax (`@theme`, `@custom-variant`, etc.) is used.

3. **Backend Independence**: The backend can run standalone via `uvicorn api:app --reload` and does not depend on the frontend.

4. **Engineering Tool**: This is a **decision-support tool**. All designs must be reviewed by qualified engineers before implementation.

## Troubleshooting

### Backend Issues

- **Import errors**: Ensure you're running from the project root or have the Python path configured correctly.
- **Port already in use**: Change the port: `uvicorn api:app --reload --port 8001`

### Frontend Issues

- **Tailwind v4 errors**: Ensure `package.json` has `tailwindcss@^3.4.1` and `globals.css` uses standard Tailwind directives (`@tailwind base`, etc.).
- **API connection errors**: Verify the backend is running on `http://localhost:8000` and CORS is enabled.

## Development

- Backend API documentation: `http://localhost:8000/docs` (Swagger UI)
- Frontend hot-reload: Enabled by default in Next.js dev mode
- Backend hot-reload: Enabled with `--reload` flag

## License

This is a professional engineering tool. Use at your own risk. All designs must be reviewed by qualified engineers.
