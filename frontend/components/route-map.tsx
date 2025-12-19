"use client"

import { useEffect, useRef, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { MapPin, Route, Ruler } from "lucide-react"

interface RoutePoint {
  lat: number
  lon: number
}

interface RouteMapProps {
  onRouteComplete?: (route: RoutePoint[], lengthKm: number, mapInstance: any) => void
  initialRoute?: RoutePoint[]
  onMapReady?: (mapInstance: any) => void
}

/**
 * Mapbox Route Drawing Component.
 * 
 * Allows user to click points on map to define route.
 * Calculates route length using Haversine formula.
 */
export default function RouteMap({ onRouteComplete, initialRoute, onMapReady }: RouteMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null)
  const [routePoints, setRoutePoints] = useState<RoutePoint[]>(initialRoute || [])
  const [routeLength, setRouteLength] = useState<number>(0)
  const [isDrawing, setIsDrawing] = useState(false)

  // Haversine formula to calculate distance between two points
  const haversineDistance = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
    const R = 6371 // Earth radius in km
    const dLat = (lat2 - lat1) * Math.PI / 180
    const dLon = (lon2 - lon1) * Math.PI / 180
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2)
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
    return R * c
  }

  // Calculate total route length
  const calculateRouteLength = (points: RoutePoint[]): number => {
    if (points.length < 2) return 0
    
    let total = 0
    for (let i = 0; i < points.length - 1; i++) {
      total += haversineDistance(
        points[i].lat,
        points[i].lon,
        points[i + 1].lat,
        points[i + 1].lon
      )
    }
    return total
  }

  useEffect(() => {
    if (!mapContainerRef.current) return

    // Dynamic import of mapbox-gl
    const loadMap = async () => {
      try {
        const mapboxgl = (await import("mapbox-gl")).default
        
        // Set access token
        mapboxgl.accessToken = "pk.eyJ1Ijoidmlyb2h1bWFuIiwiYSI6ImNtamNyaHIxODByZXAzZHJ6bXZkeWp6cnIifQ.13FV1Zte85JWq-NvrSknnw"

        // Initialize map
        const map = new mapboxgl.Map({
          container: mapContainerRef.current!,
          style: "mapbox://styles/mapbox/streets-v12",
          center: [77.2090, 28.6139], // Default: New Delhi
          zoom: 10,
        })

        mapRef.current = map
        
        // Notify parent that map is ready
        if (onMapReady) {
          onMapReady(map)
        }

        // Add click handler for route drawing
        map.on("click", (e: any) => {
          if (!isDrawing) return

          const { lng, lat } = e.lngLat
          const newPoint: RoutePoint = { lat, lon: lng }
          const updatedPoints = [...routePoints, newPoint]
          
          setRoutePoints(updatedPoints)
          
          // Update route length
          const length = calculateRouteLength(updatedPoints)
          setRouteLength(length)

          // Add marker
          new mapboxgl.Marker({ color: "#ef4444" })
            .setLngLat([lng, lat])
            .addTo(map)

          // Update route polyline
          updateRouteLine(map, updatedPoints)
        })

        map.on("load", () => {
          // Add initial route if provided
          if (initialRoute && initialRoute.length > 0) {
            updateRouteLine(map, initialRoute)
            initialRoute.forEach(point => {
              new mapboxgl.Marker({ color: "#ef4444" })
                .setLngLat([point.lon, point.lat])
                .addTo(map)
            })
          }
        })

        return () => {
          map.remove()
        }
      } catch (error) {
        console.error("Failed to load Mapbox:", error)
      }
    }

    loadMap()
  }, [])

  // Update route polyline on map
  const updateRouteLine = (map: any, points: RoutePoint[]) => {
    if (points.length < 2) return

    // Remove existing route source/layer if present
    if (map.getSource("route")) {
      map.removeLayer("route")
      map.removeSource("route")
    }

    // Create coordinates array
    const coordinates = points.map(p => [p.lon, p.lat])

    // Add route source
    map.addSource("route", {
      type: "geojson",
      data: {
        type: "Feature",
        properties: {},
        geometry: {
          type: "LineString",
          coordinates: coordinates,
        },
      },
    })

    // Add route layer
    map.addLayer({
      id: "route",
      type: "line",
      source: "route",
      layout: {
        "line-join": "round",
        "line-cap": "round",
      },
      paint: {
        "line-color": "#3b82f6",
        "line-width": 4,
      },
    })
  }

  const handleStartDrawing = () => {
    setIsDrawing(true)
    setRoutePoints([])
    setRouteLength(0)
    
    // Clear existing route from map
    if (mapRef.current) {
      if (mapRef.current.getSource("route")) {
        mapRef.current.removeLayer("route")
        mapRef.current.removeSource("route")
      }
      // Clear markers (simplified - in production, track markers)
      mapRef.current.eachLayer((layer: any) => {
        if (layer.id !== "route" && layer.type === "symbol") {
          // Skip default layers
        }
      })
    }
  }

  const handleStopDrawing = () => {
    setIsDrawing(false)
  }

  const handleClearRoute = () => {
    setRoutePoints([])
    setRouteLength(0)
    setIsDrawing(false)
    
    if (mapRef.current) {
      if (mapRef.current.getSource("route")) {
        mapRef.current.removeLayer("route")
        mapRef.current.removeSource("route")
      }
    }
  }

  const handleUseRoute = () => {
    if (routePoints.length < 2) {
      alert("Please draw a route with at least 2 points")
      return
    }
    
    if (onRouteComplete) {
      onRouteComplete(routePoints, routeLength, mapRef.current)
    }
  }

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-foreground text-lg flex items-center gap-2">
          <Route className="h-5 w-5" />
          Route Definition
        </CardTitle>
        <CardDescription>Click on the map to define your transmission line route</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Map Container */}
          <div ref={mapContainerRef} className="h-96 w-full rounded-md border border-border" />
          
          {/* Controls */}
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              type="button"
              variant={isDrawing ? "default" : "outline"}
              onClick={handleStartDrawing}
              disabled={isDrawing}
            >
              <MapPin className="h-4 w-4 mr-2" />
              Start Drawing
            </Button>
            
            {isDrawing && (
              <Button
                type="button"
                variant="outline"
                onClick={handleStopDrawing}
              >
                Stop Drawing
              </Button>
            )}
            
            <Button
              type="button"
              variant="outline"
              onClick={handleClearRoute}
              disabled={routePoints.length === 0}
            >
              Clear Route
            </Button>
            
            <Button
              type="button"
              variant="default"
              onClick={handleUseRoute}
              disabled={routePoints.length < 2}
              className="ml-auto"
            >
              Use This Route
            </Button>
          </div>
          
          {/* Route Info */}
          {routePoints.length > 0 && (
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">Points:</span>
                <span className="font-medium">{routePoints.length}</span>
              </div>
              <div className="flex items-center gap-2">
                <Ruler className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">Length:</span>
                <span className="font-medium">{routeLength.toFixed(2)} km</span>
              </div>
            </div>
          )}
          
          {routePoints.length < 2 && (
            <p className="text-xs text-muted-foreground">
              Click "Start Drawing" then click on the map to add route points. Minimum 2 points required.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

