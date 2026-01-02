/**
 * API client for backend communication
 */

/**
 * Sanitize error message to replace Unicode characters with ASCII equivalents
 * to avoid Windows console encoding issues
 * 
 * This function aggressively removes all non-ASCII characters to prevent
 * encoding errors in Windows console environments.
 */
function sanitizeErrorMessage(message: any): string {
  // Convert to string first, handle null/undefined
  if (message === null || message === undefined) {
    return "Unknown error"
  }
  
  let msg: string
  try {
    msg = String(message)
  } catch {
    return "Error occurred (could not convert to string)"
  }
  
  // Aggressively sanitize: replace ALL non-ASCII characters
  // Use a character-by-character approach to avoid encoding issues
  const chars: string[] = []
  for (let i = 0; i < msg.length; i++) {
    try {
      const char = msg[i]
      const code = char.charCodeAt(0)
      if (code <= 127) {
        // ASCII character (0-127) - safe to keep
        chars.push(char)
      } else {
        // Non-ASCII character - replace with ASCII equivalent or placeholder
        // First check for common symbols we want to replace with readable text
        if (code === 0x2264) { // ≤
          chars.push("<=")
        } else if (code === 0x2265) { // ≥
          chars.push(">=")
        } else if (code === 0x2260) { // ≠
          chars.push("!=")
        } else if (code === 0x2192) { // →
          chars.push("->")
        } else if (code === 0x2190) { // ←
          chars.push("<-")
        } else if (code === 0x00B1) { // ±
          chars.push("+/-")
        } else if (code === 0x00D7) { // ×
          chars.push("x")
        } else if (code === 0x00F7) { // ÷
          chars.push("/")
        } else {
          // Unknown non-ASCII - replace with safe placeholder
          chars.push("?")
        }
      }
    } catch (e) {
      // If we can't process this character, skip it
      chars.push("?")
    }
  }
  
  return chars.join('')
}

export async function runOptimization(payload: any) {
  const res = await fetch("http://localhost:8000/optimize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    // Try to parse JSON error response
    let rawMessage: any = `HTTP error! status: ${res.status}`
    try {
      const errorData = await res.json()
      rawMessage = errorData.detail || rawMessage
    } catch {
      // If not JSON, try text
      try {
        rawMessage = await res.text()
      } catch {
        // If text parsing also fails, use default
      }
    }
    
    // AGGRESSIVELY sanitize: Replace ALL non-ASCII characters immediately
    // Convert to string and replace every non-ASCII char with '?'
    const safeMessage = String(rawMessage || "Unknown error")
      .split('')
      .map((char: string) => {
        const code = char.charCodeAt(0)
        // Keep only ASCII characters (0-127)
        if (code <= 127) {
          return char
        }
        // Replace common Unicode symbols with ASCII equivalents
        if (char === '≤' || code === 0x2264) return '<='
        if (char === '≥' || code === 0x2265) return '>='
        if (char === '≠' || code === 0x2260) return '!='
        if (char === '→' || code === 0x2192) return '->'
        if (char === '←' || code === 0x2190) return '<-'
        if (char === '±' || code === 0x00B1) return '+/-'
        if (char === '×' || code === 0x00D7) return 'x'
        if (char === '÷' || code === 0x00F7) return '/'
        // Everything else becomes '?'
        return '?'
      })
      .join('')
    
    // Create error with 100% ASCII-safe message
    throw new Error(safeMessage)
  }

  return res.json()
}

/**
 * Normalize form data to match backend schema exactly.
 * 
 * IMPORTANT: This validates INPUT FORMAT only (enum values, types).
 * It does NOT validate physics constraints (span bounds, height limits, etc.).
 * Physics validation is the backend's responsibility.
 * 
 * Matches original optimizer input constraints:
 * - terrain: "flat" | "rolling" | "mountainous" | "desert"
 * - wind: "zone_1" | "zone_2" | "zone_3" | "zone_4"
 * - soil: "soft" | "medium" | "hard" | "rock"
 * - tower: "suspension" | "angle" | "tension" | "dead_end"
 * - voltage: integer (kV)
 */
export function normalizePayload(formData: any) {
  // Ensure voltage is an integer (backend expects int, not float)
  const voltage = Math.floor(Number(formData.voltage))
  
  // Validate enum values match backend schema exactly
  // This is format validation, NOT physics validation
  const validTerrain = ["flat", "rolling", "mountainous", "desert"]
  const validWind = ["zone_1", "zone_2", "zone_3", "zone_4"]
  const validSoil = ["soft", "medium", "hard", "rock"]
  const validTower = ["suspension", "angle", "tension", "dead_end"]
  
  if (!validTerrain.includes(formData.terrain)) {
    throw new Error(`Invalid terrain: ${formData.terrain}. Must be one of: ${validTerrain.join(", ")}`)
  }
  
  if (!validWind.includes(formData.wind)) {
    throw new Error(`Invalid wind zone: ${formData.wind}. Must be one of: ${validWind.join(", ")}`)
  }
  
  if (!validSoil.includes(formData.soil)) {
    throw new Error(`Invalid soil: ${formData.soil}. Must be one of: ${validSoil.join(", ")}`)
  }
  
  if (!validTower.includes(formData.tower)) {
    throw new Error(`Invalid tower type: ${formData.tower}. Must be one of: ${validTower.join(", ")}`)
  }
  
  // Build payload with exact field names and values expected by backend
  const payload: any = {
    voltage: voltage, // int
    soil: formData.soil, // Required: "soft" | "medium" | "hard" | "rock"
    tower: formData.tower, // Required: "suspension" | "angle" | "tension" | "dead_end"
    flags: {
      design_for_higher_wind: !!formData.flags.design_for_higher_wind,
      include_ice_load: !!formData.flags.include_ice_load,
      conservative_foundation: !!formData.flags.conservative_foundation,
    },
    row_mode: formData.row_mode || "urban_private", // Default: "urban_private"
  }
  
  // Add optional fields only if they have valid values
  if (formData.terrain && validTerrain.includes(formData.terrain)) {
    payload.terrain = formData.terrain // Optional: "flat" | "rolling" | "mountainous" | "desert"
  }
  
  if (formData.wind && validWind.includes(formData.wind)) {
    payload.wind = formData.wind // Optional: "zone_1" | "zone_2" | "zone_3" | "zone_4"
  }
  
  // Add geo_context if provided (map-driven geographic resolution)
  if (formData.geo_context) {
    payload.geo_context = {
      country_code: formData.geo_context.country_code,
      country_name: formData.geo_context.country_name,
      state: formData.geo_context.state,
      resolution_mode: formData.geo_context.resolution_mode,
    }
  }
  
  // Add project_length_km if provided (now sent to backend for canonical format)
  if (formData.projectLength) {
    const projectLengthNum = Number(formData.projectLength)
    if (!isNaN(projectLengthNum) && projectLengthNum >= 1 && projectLengthNum <= 1000) {
      payload.project_length_km = projectLengthNum
    }
  }
  
  // Add route_coordinates if provided (TASK 5.3)
  if (formData.routeCoordinates && formData.routeCoordinates.length >= 2) {
    payload.route_coordinates = formData.routeCoordinates
  }
  
  // Add terrain_profile if provided (TASK 5.3)
  // Backend expects format: [{ "x": distance_m, "z": elevation_m }]
  if (formData.terrainProfile && formData.terrainProfile.length > 0) {
    payload.terrain_profile = formData.terrainProfile.map(point => ({
      x: point.distance_m,
      z: point.elevation_m,
    }))
  }
  
  return payload
}

/**
 * Validate design after tower movement
 */
export async function validateDesign(payload: {
  towers: Array<{
    index: number
    latitude: number
    longitude: number
    total_height_m: number
    distance_along_route_m?: number
  }>
  spans: Array<{
    from_tower_index: number
    to_tower_index: number
    span_length_m: number
  }>
  voltage_kv: number
  geo_context?: {
    country_code?: string
    country_name?: string
    state?: string
  }
  route_coordinates?: Array<{ lat: number; lon: number }>
  terrain_profile?: Array<{ distance_m: number; elevation_m: number }>
}) {
  const res = await fetch("http://localhost:8000/validate-design", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    let rawMessage: any = `HTTP error! status: ${res.status}`
    try {
      const errorData = await res.json()
      rawMessage = errorData.detail || rawMessage
    } catch {
      try {
        rawMessage = await res.text()
      } catch {
        // If text parsing also fails, use default
      }
    }
    
    // AGGRESSIVELY sanitize: Replace ALL non-ASCII characters immediately
    const safeMessage = String(rawMessage || "Unknown error")
      .split('')
      .map((char: string) => {
        const code = char.charCodeAt(0)
        if (code <= 127) return char
        if (char === '≤' || code === 0x2264) return '<='
        if (char === '≥' || code === 0x2265) return '>='
        if (char === '≠' || code === 0x2260) return '!='
        if (char === '→' || code === 0x2192) return '->'
        if (char === '←' || code === 0x2190) return '<-'
        if (char === '±' || code === 0x00B1) return '+/-'
        if (char === '×' || code === 0x00D7) return 'x'
        if (char === '÷' || code === 0x00F7) return '/'
        return '?'
      })
      .join('')
    
    throw new Error(safeMessage)
  }

  return res.json()
}

/**
 * Validate foundation safety for all towers
 */
export async function validateFoundationSafety(payload: {
  towers: Array<any>
  project_location: string
  voltage: number
  terrain: "flat" | "rolling" | "mountainous" | "desert"
  wind: "zone_1" | "zone_2" | "zone_3" | "zone_4"
  soil: "soft" | "medium" | "hard" | "rock"
  design_for_higher_wind?: boolean
  include_ice_load?: boolean
  include_broken_wire?: boolean
  auto_correct?: boolean
}) {
  const res = await fetch("http://localhost:8000/validate-foundation-safety", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    let rawMessage: any = `HTTP error! status: ${res.status}`
    try {
      const errorData = await res.json()
      rawMessage = errorData.detail || rawMessage
    } catch {
      try {
        rawMessage = await res.text()
      } catch {
        // If text parsing also fails, use default
      }
    }
    
    // AGGRESSIVELY sanitize: Replace ALL non-ASCII characters immediately
    const safeMessage = String(rawMessage || "Unknown error")
      .split('')
      .map((char: string) => {
        const code = char.charCodeAt(0)
        if (code <= 127) return char
        if (char === '≤' || code === 0x2264) return '<='
        if (char === '≥' || code === 0x2265) return '>='
        if (char === '≠' || code === 0x2260) return '!='
        if (char === '→' || code === 0x2192) return '->'
        if (char === '←' || code === 0x2190) return '<-'
        if (char === '±' || code === 0x00B1) return '+/-'
        if (char === '×' || code === 0x00D7) return 'x'
        if (char === '÷' || code === 0x00F7) return '/'
        return '?'
      })
      .join('')
    
    throw new Error(safeMessage)
  }

  return res.json()
}

