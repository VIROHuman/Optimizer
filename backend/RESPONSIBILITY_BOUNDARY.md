# Responsibility Boundary: Frontend vs Backend

## CRITICAL RULE

**Frontend collects inputs. Backend owns physics.**

## Frontend Responsibilities

✅ **DO:**
- Collect raw user inputs (location, voltage, terrain, wind, soil, tower type)
- Validate input format (e.g., voltage is a number)
- Normalize data format (e.g., lowercase location, integer voltage)
- Display results from backend
- Handle loading and error states

❌ **DO NOT:**
- Calculate span length, tower height, or any geometry
- Enforce physics constraints (e.g., span must be 250-450m)
- Validate engineering limits
- Throw errors for physics violations
- Re-validate backend outputs
- Modify or clamp backend results

## Backend Responsibilities

✅ **DO:**
- Enforce ALL physics constraints and bounds
- Guarantee returned designs are within valid ranges (or flagged as violations)
- Clamp values during optimization, not after
- Return structured responses with violations, never crash
- Log warnings for bounds violations (indicates optimizer bug)
- Own span bounds (250-450m), height bounds (25-60m), footing bounds, etc.

❌ **DO NOT:**
- Rely on frontend for validation
- Return invalid geometry without violation flags
- Raise exceptions for physics violations (return violations instead)
- Use different default bounds than original optimizer

## Span Length Bug (Fixed)

**Root Cause:** Backend service used wrong default span bounds (200-600m) instead of original (250-450m).

**Fix:**
1. Changed defaults in `optimizer_service.py` to match original (250-450m)
2. Removed `ValueError` raises from `TowerDesign.__post_init__`
3. Added defensive bounds checking in optimizer
4. Added post-optimization validation that logs warnings and adds violations
5. Ensured API never crashes, always returns structured response

## Enforcement

- **Optimizer** clamps span to bounds in `_decode_position()` method
- **Service** validates bounds after optimization and adds violations if needed
- **API** catches all exceptions and returns structured error responses
- **Frontend** never validates physics - only displays backend results

## Why This Matters

If frontend validates physics:
- Backend bugs can be masked
- Inconsistent behavior between CLI and API
- Violations go unreported
- System becomes brittle

If backend doesn't enforce bounds:
- Invalid designs can be returned
- Runtime errors occur
- Engineering tool becomes unreliable
- Violations are thrown as exceptions instead of reported



