# Global Transmission Line Optimization System

A decision-support tool for optimizing overhead transmission tower designs using Particle Swarm Optimization (PSO). This system provides globally applicable, transparent, and engineer-driven optimization while respecting regional design standards and constraints.

## ⚠️ Important Notice

**THIS IS A DECISION-SUPPORT TOOL. IT DOES NOT REPLACE ENGINEERS.**

All designs must be reviewed by qualified engineers before construction. The system evaluates explicitly selected design scenarios. Region-dominant risks may govern final design and must be assessed based on project requirements.

## Recent Changes

### Frontend Rollback (Latest)

The frontend integration (Next.js/React/Tailwind) has been completely removed. The system now operates as a **CLI-only Python application**. All frontend files, dependencies, and build artifacts have been removed to restore the repository to a clean backend-only state.

**Removed:**
- Next.js frontend (`/app`, `/components`, `/public`, `/styles`)
- Node.js dependencies (`package.json`, `node_modules`)
- Frontend build configs (`next.config.mjs`, `tailwind.config.js`, `postcss.config.mjs`, `tsconfig.json`)
- All frontend-related lockfiles

**Preserved:**
- Complete backend optimization engine
- CLI interface (`main.py`)
- Intelligence module (crawlers, validators, reference store)
- API layer (`backend/api.py`) - available but not required for CLI usage

## Quick Start

### Prerequisites

- Python 3.8+
- Required Python packages (install via `pip`)

### Installation

```bash
# Clone or navigate to the project directory
cd Optimiser

# Install Python dependencies
pip install numpy scipy requests fastapi uvicorn
```

### Basic Usage

Run optimization via command-line interface:

```bash
python main.py \
  --location "India" \
  --voltage 400 \
  --terrain flat \
  --wind zone_2 \
  --soil medium \
  --tower suspension
```

### Example Output

The system will:
1. Automatically determine the governing design standard (IS/IEC/Eurocode/ASCE)
2. Run PSO optimization to find optimal tower geometry
3. Display optimized design parameters
4. Show cost breakdown (tower cost, ROW costs, line-level economics)
5. Provide safety confirmations and regional risk advisories
6. Display reference data status (currency rates, cost indices)

## System Architecture

### Core Components

```
Optimiser/
├── main.py                    # CLI entry point
├── pso_optimizer.py          # PSO optimization engine
├── cost_engine.py            # Cost calculation (tower + ROW)
├── codal_engine/            # Design standard implementations
│   ├── is_engine.py         # IS 802 (India)
│   ├── iec_engine.py        # IEC 60826 (International)
│   ├── eurocode_engine.py   # EN 50341 (Europe)
│   └── asce_engine.py       # ASCE 10-15 (USA)
├── constructability_engine.py # Constructability checks
├── data_models.py           # Core data structures
├── location_to_code.py      # Auto-resolve design standard
├── regional_risk_registry.py # Regional risk database
├── dominant_risk_advisory.py # Risk escalation logic
└── intelligence/            # Live data intelligence module
    ├── currency_crawler.py  # FX rate tracking
    ├── cost_crawler.py      # Cost index monitoring
    ├── risk_crawler.py      # Risk alert detection
    ├── code_crawler.py      # Standards revision alerts
    ├── validator.py         # Human approval gate
    ├── reference_store.py   # Versioned reference data
    ├── intelligence_manager.py # Intelligence orchestration
    └── run_crawlers.py      # Crawler execution
```

### Backend API (Optional)

An optional FastAPI backend is available for programmatic access:

```bash
# Start API server
uvicorn backend.api:app --host 0.0.0.0 --port 8000

# Or run directly
python backend/api.py
```

The API exposes:
- `POST /optimize` - Run optimization
- `GET /health` - Health check

See `README_API.md` for detailed API documentation.

## Key Features

### 1. Global Applicability

- **Automatic Standard Detection**: System automatically selects the governing design standard based on project location
- **Multi-Standard Support**: IS, IEC, Eurocode, ASCE
- **No Hardcoded Limits**: Region-specific constraints come from design standards, not hardcoded values

### 2. Right-of-Way (ROW) Cost Modeling

The system models ROW as two components:

- **Corridor ROW (Dominant)**: `corridor_width × land_rate × 1000` per km
  - Represents compensation under conductors, land devaluation, easements
  - Region-configurable corridor widths (40-70m typical)
  - Dominates land economics in dense regions

- **Tower Footprint ROW (Secondary)**: `(base_width² × land_rate) × towers_per_km`
  - Secondary component
  - Included in line-level optimization objective

### 3. Ice Load Coupling

When `--include-ice-load` is enabled:
- Increases vertical load on conductors
- Propagates into cross-arm demand, vertical reactions, foundation bearing/uplift
- Influences steel demand and geometry trade-offs
- Uses conservative envelope approach (not full catenary analysis)

### 4. Region-Dominant Risk Advisories

- Classifies risks as "Informational" or "Dominant (Often Governing)"
- Escalates severity for high-voltage (≥220 kV) projects in regions where risks historically govern
- **Never auto-enables scenarios** - engineers retain full control
- Provides actionable recommendations

### 5. Live Intelligence Module

**Architectural Principle: "LIVE DATA MAY INFORM, NEVER DECIDE."**

- **Crawlers**: Fetch live data (currency rates, cost indices, risk alerts, code revisions)
- **Validator**: Requires explicit human approval for all updates
- **Reference Store**: Versioned storage of approved data
- **Intelligence Manager**: Read-only access to approved data for display/formatting

**Usage:**
```bash
# Run crawlers to fetch live data
python intelligence/run_crawlers.py

# Review and approve pending updates
python intelligence/approve_updates.py --list
python intelligence/approve_updates.py --approve-all --approved-by "Engineer Name"

# Schedule crawlers (optional)
python intelligence/scheduler.py --once
```

### 6. Currency Display

- **India Projects**: Costs displayed in INR (₹) using approved USD→INR rate
- **All Other Regions**: Costs displayed in USD ($)
- **Internal Optimization**: Always uses USD (currency conversion is display-only)

## Command-Line Options

### Required Arguments

- `--location`: Project location (country/region, e.g., "India", "UAE", "USA")
- `--voltage`: Voltage level in kV (e.g., 132, 220, 400, 765)
- `--terrain`: Terrain type (`flat`, `rolling`, `mountainous`, `desert`)
- `--wind`: Wind zone (`zone_1`, `zone_2`, `zone_3`, `zone_4`, or `1`, `2`, `3`, `4`)
- `--soil`: Soil category (`soft`, `medium`, `hard`, `rock`)

### Optional Arguments

- `--tower`: Tower type (`suspension`, `angle`, `tension`, `dead_end`) - Default: `suspension`
- `--span-min`: Minimum span length in meters - Default: `250.0`
- `--span-max`: Maximum span length in meters - Default: `450.0`
- `--particles`: Number of PSO particles - Default: `30`
- `--iterations`: Maximum PSO iterations - Default: `100`
- `--design-for-higher-wind`: Enable higher wind design scenario
- `--include-ice-load`: Enable ice load scenario
- `--high-reliability`: Enable high reliability design
- `--conservative-foundation`: Use conservative foundation design

### Example Commands

```bash
# Basic optimization
python main.py --location "India" --voltage 400 --terrain flat --wind zone_2 --soil medium

# With ice load and high reliability
python main.py --location "Germany" --voltage 220 --terrain rolling --wind zone_3 --soil medium \
  --include-ice-load --high-reliability

# Custom span range and PSO parameters
python main.py --location "USA" --voltage 765 --terrain mountainous --wind zone_4 --soil hard \
  --span-min 300 --span-max 500 --particles 50 --iterations 150
```

## Output Sections

The system provides comprehensive output:

1. **Project Context**: Location, voltage, terrain, governing standard
2. **Optimized Design**: Tower geometry (height, base width, cross-arm length, etc.)
3. **Cost Breakdown**: Tower cost, foundation cost, ROW costs (corridor + footprint)
4. **Line-Level Economics**: Span length, towers per km, total cost per km
5. **Safety Status**: Codal compliance checks, factor of safety confirmations
6. **Constructability Warnings**: Feasibility checks and recommendations
7. **Regional Risk Context**: Region-specific risk information
8. **Dominant Risk Advisories**: Escalated warnings for high-voltage projects
9. **Reference Data Status**: Currency rates, cost indices, data versions
10. **Design Scenarios Applied**: Summary of enabled design scenarios

## Expected Global Behavior

After optimization, the system exhibits region-appropriate behavior:

- **Germany/Europe**: Base widths shrink naturally, towers become taller & slimmer, €/km increases toward realistic EPC ranges
- **India (Rural)**: ROW corridor cost smaller, moderate base widths acceptable, €/km remains competitive
- **Desert/Remote Regions**: ROW minimal, steel vs logistics dominates

**No region-specific geometry hacks** - behavior emerges naturally from physics, codes, and economics.

## Intelligence Module Workflow

### 1. Fetch Live Data

```bash
python intelligence/run_crawlers.py
```

This will:
- Fetch USD→INR exchange rates (Yahoo Finance, Fixer.io fallback)
- Fetch cost indices (steel, cement, labor, fuel)
- Monitor risk alerts (seismic, flood, cyclone, climate)
- Detect code standard revisions

All fetched data is stored as **PENDING** and requires approval.

### 2. Review Pending Updates

```bash
python intelligence/approve_updates.py --list
```

### 3. Approve Updates

```bash
# Approve specific update
python intelligence/approve_updates.py --approve <data_id> --approved-by "Engineer Name"

# Approve all pending updates
python intelligence/approve_updates.py --approve-all --approved-by "Engineer Name"
```

### 4. Approved Data Usage

Once approved, data is:
- Stored in `reference_data/approved/` with versioning
- Available to `IntelligenceManager` for display/formatting
- **Never** consumed by PSO or physics calculations
- Used only for currency conversion (display-only) and advisory generation

## File Structure

```
Optimiser/
├── main.py                          # CLI entry point
├── pso_optimizer.py                 # PSO optimization engine
├── cost_engine.py                   # Cost calculations
├── constructability_engine.py       # Constructability checks
├── data_models.py                   # Core data structures
├── location_to_code.py              # Standard resolution
├── regional_risk_registry.py        # Regional risks
├── dominant_risk_advisory.py        # Risk advisories
├── backend/
│   ├── api.py                       # FastAPI server (optional)
│   └── services/
│       └── optimizer_service.py     # Shared optimization logic
├── codal_engine/                    # Design standard engines
│   ├── base.py                      # Base engine interface
│   ├── is_engine.py                 # IS 802 (India)
│   ├── iec_engine.py                # IEC 60826 (International)
│   ├── eurocode_engine.py           # EN 50341 (Europe)
│   └── asce_engine.py               # ASCE 10-15 (USA)
├── intelligence/                    # Live data intelligence
│   ├── currency_crawler.py          # FX rate crawler
│   ├── cost_crawler.py              # Cost index crawler
│   ├── risk_crawler.py              # Risk alert crawler
│   ├── code_crawler.py              # Code revision crawler
│   ├── validator.py                 # Approval gate
│   ├── reference_store.py           # Versioned data store
│   ├── intelligence_manager.py      # Intelligence orchestration
│   ├── run_crawlers.py              # Crawler runner
│   ├── approve_updates.py          # Approval CLI
│   └── scheduler.py                 # Scheduled crawler execution
└── reference_data/                  # Reference data storage
    ├── pending_updates.json         # Pending approvals (single source of truth)
    └── approved/                    # Approved data (versioned)
        ├── currency_rate_*.json
        ├── cost_index_*.json
        └── risk_alert_*.json
```

## Development

### Adding New Design Standards

1. Create new engine in `codal_engine/` inheriting from `CodalEngine`
2. Implement required methods (safety checks, load calculations)
3. Register in `location_to_code.py` if location-based

### Adding New Crawlers

1. Create crawler in `intelligence/` following existing patterns
2. Return structured data (dataclass with metadata)
3. Register in `run_crawlers.py`
4. Ensure all fetched data goes through `validator.request_approval()`

### Modifying Cost Models

- Edit `cost_engine.py` for cost calculation logic
- Ensure ROW corridor cost is included in line-level objective
- Maintain separation: cost engine does not interpret codes

## License

[Specify your license here]

## Disclaimer

This tool evaluates explicitly selected design scenarios. Region-dominant risks may govern final design and must be assessed based on project requirements. All designs must be reviewed by qualified engineers before construction.

---

**Last Updated**: December 2025  
**Status**: CLI-only backend (frontend rolled back)

