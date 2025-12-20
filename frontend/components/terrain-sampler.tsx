"use client"

import { useEffect, useState, useRef } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Mountain, Loader2 } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

interface RoutePoint {
  lat: number
  lon: number
}

interface TerrainPoint {
  distance_m: number
  elevation_m: number
}

interface TerrainSamplerProps {
  routePoints: RoutePoint[]
  mapInstance: any
  onTerrainComplete?: (profile: TerrainPoint[]) => void
}

/**
 * Terrain Sampling Component.
 * 
 * Samples elevation every ~30 meters along route using Mapbox terrain API.
 */
export default function TerrainSampler({ routePoints, mapInstance, onTerrainComplete }: TerrainSamplerProps) {
  const [terrainProfile, setTerrainProfile] = useState<TerrainPoint[]>([])
  const [isSampling, setIsSampling] = useState(false)
  const [samplingProgress, setSamplingProgress] = useState(0)
  const tileCacheRef = useRef<Map<string, ImageData>>(new Map())

  // Calculate distance between two points (Haversine, in meters)
  const haversineDistanceM = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
    const R = 6371000 // Earth radius in meters
    const dLat = (lat2 - lat1) * Math.PI / 180
    const dLon = (lon2 - lon1) * Math.PI / 180
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2)
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
    return R * c
  }

  // Interpolate points along route every ~30m
  const interpolateRoutePoints = (points: RoutePoint[], intervalM: number = 30): RoutePoint[] => {
    if (points.length < 2) return points

    const interpolated: RoutePoint[] = [points[0]] // Start with first point

    for (let i = 0; i < points.length - 1; i++) {
      const p1 = points[i]
      const p2 = points[i + 1]
      const segmentDistance = haversineDistanceM(p1.lat, p1.lon, p2.lat, p2.lon)
      const numIntervals = Math.floor(segmentDistance / intervalM)

      for (let j = 1; j <= numIntervals; j++) {
        const ratio = (j * intervalM) / segmentDistance
        const lat = p1.lat + (p2.lat - p1.lat) * ratio
        const lon = p1.lon + (p2.lon - p1.lon) * ratio
        interpolated.push({ lat, lon })
      }

      // Always include the endpoint
      if (i === points.length - 2) {
        interpolated.push(p2)
      }
    }

    return interpolated
  }

  // Convert lat/lon to tile coordinates
  const latLonToTile = (lat: number, lon: number, z: number): { x: number; y: number } => {
    const n = Math.pow(2, z)
    const x = Math.floor((lon + 180) / 360 * n)
    const latRad = (lat * Math.PI) / 180
    const y = Math.floor((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2 * n)
    return { x, y }
  }

  // Get pixel coordinates within a tile
  const getPixelCoordinates = (lat: number, lon: number, tileX: number, tileY: number, z: number): { px: number; py: number } => {
    const n = Math.pow(2, z)
    const x = (lon + 180) / 360 * n
    const y = (1 - Math.log(Math.tan((lat * Math.PI) / 180) + 1 / Math.cos((lat * Math.PI) / 180)) / Math.PI) / 2 * n
    const px = Math.floor((x - tileX) * 256)
    const py = Math.floor((y - tileY) * 256)
    return { px: Math.max(0, Math.min(255, px)), py: Math.max(0, Math.min(255, py)) }
  }

  // Decode elevation from RGB using Mapbox formula
  const decodeElevation = (r: number, g: number, b: number): number => {
    // Mapbox Terrain-RGB formula: elevation_m = -10000 + (R * 256 * 256 + G * 256 + B) * 0.1
    return -10000 + (r * 256 * 256 + g * 256 + b) * 0.1
  }

  // Fetch Terrain-RGB tile and get elevation at point
  const getElevationFromTerrainRGB = async (lat: number, lon: number): Promise<number> => {
    const z = 14 // Use zoom level 14 for good resolution
    const tile = latLonToTile(lat, lon, z)
    const pixel = getPixelCoordinates(lat, lon, tile.x, tile.y, z)
    const tileKey = `${z}/${tile.x}/${tile.y}`

    // Check cache first
    if (tileCacheRef.current.has(tileKey)) {
      const imageData = tileCacheRef.current.get(tileKey)!
      const pixelIndex = (pixel.py * 256 + pixel.px) * 4
      const r = imageData.data[pixelIndex]
      const g = imageData.data[pixelIndex + 1]
      const b = imageData.data[pixelIndex + 2]
      return decodeElevation(r, g, b)
    }

    // Mapbox Terrain-RGB tile URL
    const accessToken = "pk.eyJ1Ijoidmlyb2h1bWFuIiwiYSI6ImNtamNyaHIxODByZXAzZHJ6bXZkeWp6cnIifQ.13FV1Zte85JWq-NvrSknnw"
    const tileUrl = `https://api.mapbox.com/v4/mapbox.terrain-rgb/${z}/${tile.x}/${tile.y}.png?access_token=${accessToken}`

    return new Promise((resolve) => {
      const img = new Image()
      
      img.onload = () => {
        const canvas = document.createElement('canvas')
        canvas.width = 256
        canvas.height = 256
        const ctx = canvas.getContext('2d', { willReadFrequently: true })
        
        if (!ctx) {
          console.warn(`Failed to get canvas context for tile ${tileKey}`)
          resolve(0)
          return
        }

        ctx.drawImage(img, 0, 0)
        
        // Get full image data and cache it
        const imageData = ctx.getImageData(0, 0, 256, 256)
        tileCacheRef.current.set(tileKey, imageData)
        
        // Get pixel RGB values
        const pixelIndex = (pixel.py * 256 + pixel.px) * 4
        const r = imageData.data[pixelIndex]
        const g = imageData.data[pixelIndex + 1]
        const b = imageData.data[pixelIndex + 2]
        
        // Decode elevation using Mapbox formula
        const elevation = decodeElevation(r, g, b)
        resolve(elevation)
      }
      
      img.onerror = () => {
        console.warn(`Failed to load terrain tile: ${tileKey}`)
        resolve(0)
      }
      
      // Enable CORS for cross-origin image loading
      img.crossOrigin = 'anonymous'
      img.src = tileUrl
    })
  }

  const sampleTerrain = async () => {
    if (!mapInstance || routePoints.length < 2) {
      alert("Please draw a route first")
      return
    }

    setIsSampling(true)
    setSamplingProgress(0)
    setTerrainProfile([])

    try {
      // Interpolate route points every ~30m
      const interpolatedPoints = interpolateRoutePoints(routePoints, 30)
      const profile: TerrainPoint[] = []
      let cumulativeDistance = 0

      console.log(`Sampling terrain for ${interpolatedPoints.length} points...`)

      for (let i = 0; i < interpolatedPoints.length; i++) {
        const point = interpolatedPoints[i]
        
        // Get elevation from Terrain-RGB tiles
        const elevation_m = await getElevationFromTerrainRGB(point.lat, point.lon)

        // Calculate cumulative distance
        if (i > 0) {
          const prevPoint = interpolatedPoints[i - 1]
          cumulativeDistance += haversineDistanceM(
            prevPoint.lat,
            prevPoint.lon,
            point.lat,
            point.lon
          )
        }

        profile.push({
          distance_m: cumulativeDistance,
          elevation_m: elevation_m,
        })

        // Update progress
        setSamplingProgress((i + 1) / interpolatedPoints.length * 100)
        
        // Small delay to prevent rate limiting
        if (i % 5 === 0) {
          await new Promise(resolve => setTimeout(resolve, 50))
        }
      }

      // Validate elevation data
      const elevations = profile.map(p => p.elevation_m)
      const minElevation = Math.min(...elevations)
      const maxElevation = Math.max(...elevations)
      const avgElevation = elevations.reduce((a, b) => a + b, 0) / elevations.length
      const allSame = elevations.every(e => Math.abs(e - elevations[0]) < 0.1)

      console.log(`Terrain sampling complete:`)
      console.log(`  Points sampled: ${profile.length}`)
      console.log(`  Min elevation: ${minElevation.toFixed(2)} m`)
      console.log(`  Max elevation: ${maxElevation.toFixed(2)} m`)
      console.log(`  Avg elevation: ${avgElevation.toFixed(2)} m`)
      console.log(`  Elevation range: ${(maxElevation - minElevation).toFixed(2)} m`)

      if (allSame) {
        console.warn(`WARNING: All elevations are identical (${elevations[0].toFixed(2)} m). Terrain sampling may have failed.`)
        alert(`Warning: All elevation values are identical. Terrain sampling may not be working correctly.`)
      }

      if (Math.abs(maxElevation - minElevation) < 1) {
        console.warn(`WARNING: Very small elevation variation (${(maxElevation - minElevation).toFixed(2)} m). Route may be very flat or sampling failed.`)
      }

      setTerrainProfile(profile)
      
      if (onTerrainComplete) {
        onTerrainComplete(profile)
      }
    } catch (error) {
      console.error("Terrain sampling error:", error)
      alert("Failed to sample terrain. Check console for details.")
      
      // Fallback: create simple profile with zero elevation
      const fallbackProfile: TerrainPoint[] = []
      let cumulativeDistance = 0
      
      for (let i = 0; i < routePoints.length; i++) {
        if (i > 0) {
          cumulativeDistance += haversineDistanceM(
            routePoints[i - 1].lat,
            routePoints[i - 1].lon,
            routePoints[i].lat,
            routePoints[i].lon
          )
        }
        fallbackProfile.push({
          distance_m: cumulativeDistance,
          elevation_m: 0,
        })
      }
      
      setTerrainProfile(fallbackProfile)
      if (onTerrainComplete) {
        onTerrainComplete(fallbackProfile)
      }
    } finally {
      setIsSampling(false)
      setSamplingProgress(0)
    }
  }

  if (routePoints.length < 2) {
    return null
  }

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-foreground text-lg flex items-center gap-2">
          <Mountain className="h-5 w-5" />
          Terrain Profile
        </CardTitle>
        <CardDescription>Sample elevation along route</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <Button
            type="button"
            onClick={sampleTerrain}
            disabled={isSampling || routePoints.length < 2}
            className="w-full"
          >
            {isSampling ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Sampling... {samplingProgress.toFixed(0)}%
              </>
            ) : (
              <>
                <Mountain className="h-4 w-4 mr-2" />
                Sample Terrain Elevation
              </>
            )}
          </Button>

          {terrainProfile.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Sampled {terrainProfile.length} points along route
              </p>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={terrainProfile}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="distance_m" 
                      label={{ value: "Distance (m)", position: "insideBottom", offset: -5 }}
                    />
                    <YAxis 
                      label={{ value: "Elevation (m)", angle: -90, position: "insideLeft" }}
                    />
                    <Tooltip 
                      formatter={(value: number) => [`${value.toFixed(1)} m`, "Elevation"]}
                      labelFormatter={(value: number) => `Distance: ${value.toFixed(0)} m`}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="elevation_m" 
                      stroke="#3b82f6" 
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}


