"use client"

import { useEffect, useState } from "react"
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

      for (let i = 0; i < interpolatedPoints.length; i++) {
        const point = interpolatedPoints[i]
        
        // Query terrain elevation at this point
        const elevation = mapInstance.queryTerrainElevation([point.lon, point.lat])
        
        // If elevation is null, try to get from map (may not be available)
        const elevation_m = elevation !== null ? elevation : 0

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
        
        // Small delay to prevent UI blocking
        if (i % 10 === 0) {
          await new Promise(resolve => setTimeout(resolve, 10))
        }
      }

      setTerrainProfile(profile)
      
      if (onTerrainComplete) {
        onTerrainComplete(profile)
      }
    } catch (error) {
      console.error("Terrain sampling error:", error)
      alert("Failed to sample terrain. Using default elevation profile.")
      
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

