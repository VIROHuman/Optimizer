/**
 * API client for backend communication
 */

export async function runOptimization(payload: any) {
  const res = await fetch("http://localhost:8000/optimize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    // Try to parse JSON error response
    let errorMessage = `HTTP error! status: ${res.status}`
    try {
      const errorData = await res.json()
      errorMessage = errorData.detail || errorMessage
    } catch {
      // If not JSON, try text
      const errorText = await res.text()
      errorMessage = errorText || errorMessage
    }
    throw new Error(errorMessage)
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
  
  const payload: any = {
    voltage: voltage,
    terrain: formData.terrain,
    wind: formData.wind,
    soil: formData.soil,
    tower: formData.tower,
    flags: {
      design_for_higher_wind: !!formData.flags.design_for_higher_wind,
      include_ice_load: !!formData.flags.include_ice_load,
      conservative_foundation: !!formData.flags.conservative_foundation,
    },
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

