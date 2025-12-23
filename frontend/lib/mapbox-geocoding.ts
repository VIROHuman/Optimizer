/**
 * Mapbox Reverse Geocoding Service
 * 
 * Resolves country_code, country_name, and state from route coordinates.
 */

export interface GeoContext {
  country_code: string | null
  country_name: string | null
  state: string | null
  resolution_mode: "map-derived" | "user-provided" | "unresolved"
}

const MAPBOX_ACCESS_TOKEN = "pk.eyJ1Ijoidmlyb2h1bWFuIiwiYSI6ImNtamNyaHIxODByZXAzZHJ6bXZkeWp6cnIifQ.13FV1Zte85JWq-NvrSknnw"

/**
 * Reverse geocode a single coordinate using Mapbox Geocoding API
 */
export async function reverseGeocodeCoordinate(
  lat: number,
  lon: number
): Promise<GeoContext> {
  try {
    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${lon},${lat}.json?access_token=${MAPBOX_ACCESS_TOKEN}&types=country,region`
    
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Mapbox API error: ${response.status}`)
    }
    
    const data = await response.json()
    
    // Extract country and state from features
    let country_code: string | null = null
    let country_name: string | null = null
    let state: string | null = null
    
    for (const feature of data.features || []) {
      const context = feature.context || []
      
      // Find country
      const countryContext = context.find((ctx: any) => ctx.id?.startsWith("country"))
      if (countryContext) {
        country_code = countryContext.short_code?.toUpperCase() || null
        country_name = countryContext.text || null
      }
      
      // Find state/region
      const regionContext = context.find((ctx: any) => 
        ctx.id?.startsWith("region") || ctx.id?.startsWith("district")
      )
      if (regionContext) {
        state = regionContext.text || null
      }
    }
    
    // Fallback: check if feature itself is a country
    if (!country_code && data.features && data.features.length > 0) {
      const firstFeature = data.features[0]
      if (firstFeature.id?.startsWith("country")) {
        country_code = firstFeature.properties?.short_code?.toUpperCase() || null
        country_name = firstFeature.text || null
      }
    }
    
    return {
      country_code,
      country_name,
      state,
      resolution_mode: country_code ? "map-derived" : "unresolved"
    }
  } catch (error) {
    console.error("Reverse geocoding failed:", error)
    return {
      country_code: null,
      country_name: null,
      state: null,
      resolution_mode: "unresolved"
    }
  }
}

/**
 * Reverse geocode route coordinates and return the most common country
 */
export async function reverseGeocodeRoute(
  coordinates: Array<{ lat: number; lon: number }>
): Promise<GeoContext> {
  if (!coordinates || coordinates.length === 0) {
    return {
      country_code: null,
      country_name: null,
      state: null,
      resolution_mode: "unresolved"
    }
  }
  
  // Use first coordinate for country detection (most efficient)
  // For state, we could sample multiple points, but for now use first
  const firstCoord = coordinates[0]
  return reverseGeocodeCoordinate(firstCoord.lat, firstCoord.lon)
}

