# Transmission Tower Optimization API

## Backend Setup

### Install Dependencies

```bash
pip install fastapi uvicorn
```

### Run API Server

```bash
python backend/api.py
```

Or using uvicorn directly:

```bash
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### POST /optimize

Run transmission tower optimization.

**Request Body:**
```json
{
  "location": "india",
  "voltage": 400,
  "terrain": "flat",
  "wind": "zone_2",
  "soil": "medium",
  "tower": "suspension",
  "design_for_higher_wind": false,
  "include_ice_load": false,
  "conservative_foundation": false,
  "high_reliability": false,
  "span_min": 200.0,
  "span_max": 600.0,
  "particles": 30,
  "iterations": 100
}
```

**Response:**
See `OptimizationResponse` type in `lib/api.ts` for full structure.

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

## Frontend Configuration

Set the API URL in `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Or it will default to `http://localhost:8000`.

## CORS

CORS is enabled for:
- `http://localhost:3000`
- `http://localhost:3001`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:3001`

## CLI Still Works

The CLI (`main.py`) continues to work independently:

```bash
python main.py --location "India" --voltage 400 --terrain flat --wind zone_2 --soil medium --tower suspension
```

