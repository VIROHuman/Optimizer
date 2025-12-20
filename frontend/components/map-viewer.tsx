"use client"

import { useEffect, useRef } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface MapViewerProps {
  towers: Array<{
    index: number
    latitude?: number
    longitude?: number
    total_height_m: number
    distance_along_route_m: number
  }>
  spans: Array<{
    from_tower_index: number
    to_tower_index: number
    span_length_m: number
  }>
  routeCoordinates?: Array<{ lat: number; lon: number }>
}

/**
 * Mapbox GL Viewer (Read-Only).
 * 
 * Displays route polyline, tower markers, and tower height scaling.
 * NO calculations on map - purely visual representation of backend data.
 */
export default function MapViewer({ towers, spans, routeCoordinates }: MapViewerProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null)

  useEffect(() => {
    // Only initialize if we have coordinates
    if (!towers.length || !towers[0].latitude || !towers[0].longitude) {
      return
    }

    // Dynamic import of mapbox-gl (free tier)
    const loadMap = async () => {
      try {
        const mapboxgl = await import("mapbox-gl")
        
        if (!mapboxgl.accessToken) {
          // Use free public token or require user to provide
          console.warn("Mapbox token not set. Map will not render.")
          return
        }

        if (!mapContainerRef.current) return

        // Initialize map
        const map = new mapboxgl.Map({
          container: mapContainerRef.current,
          style: "mapbox://styles/mapbox/streets-v12",
          center: [towers[0].longitude!, towers[0].latitude!],
          zoom: 12,
        })

        mapRef.current = map

        // Add route polyline
        if (routeCoordinates && routeCoordinates.length > 0) {
          const coordinates = routeCoordinates.map(coord => [coord.lon, coord.lat])
          
          map.on("load", () => {
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
          })
        }

        // Add tower markers
        towers.forEach((tower) => {
          if (tower.latitude && tower.longitude) {
            const el = document.createElement("div")
            el.className = "tower-marker"
            el.style.width = "20px"
            el.style.height = "20px"
            el.style.borderRadius = "50%"
            el.style.backgroundColor = "#ef4444"
            el.style.border = "2px solid white"
            el.style.cursor = "pointer"
            el.title = `Tower ${tower.index}: ${tower.total_height_m.toFixed(1)}m`

            new mapboxgl.Marker(el)
              .setLngLat([tower.longitude, tower.latitude])
              .addTo(map)
          }
        })

        return () => {
          map.remove()
        }
      } catch (error) {
        console.error("Failed to load map:", error)
      }
    }

    loadMap()
  }, [towers, routeCoordinates])

  // If no coordinates, show placeholder
  if (!towers.length || !towers[0].latitude || !towers[0].longitude) {
    return (
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle>Map View</CardTitle>
          <CardDescription>Route visualization (requires GPS coordinates)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-96 bg-muted rounded-md flex items-center justify-center">
            <p className="text-muted-foreground">No GPS coordinates available for map display</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-card border-border">
      <CardHeader>
        <CardTitle>Map View</CardTitle>
        <CardDescription>Route polyline and tower locations (read-only)</CardDescription>
      </CardHeader>
      <CardContent>
        <div ref={mapContainerRef} className="h-96 w-full rounded-md" />
        <p className="text-xs text-muted-foreground mt-2">
          Note: Map is read-only. Tower positions are determined by backend optimization.
        </p>
      </CardContent>
    </Card>
  )
}


