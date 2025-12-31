"use client"

import { useEffect, useRef, useMemo } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertCircle } from "lucide-react"

interface MapViewerProps {
  towers: Array<{
    index: number
    latitude?: number
    longitude?: number
    total_height_m: number
    distance_along_route_m: number
    nudge_description?: string
    original_distance_m?: number
  }>
  spans: Array<{
    from_tower_index: number
    to_tower_index: number
    span_length_m: number
  }>
  routeCoordinates?: Array<{ lat: number; lon: number }>
  obstacles?: Array<{
    start_distance_m: number
    end_distance_m: number
    type: string
    name?: string
    geometry?: Array<{ lat: number; lon: number }>
    metadata?: any
  }>
  voltage_kv?: number
  geo_context?: any
}

/**
 * Mapbox GL Viewer (Read-Only).
 * 
 * Displays route polyline, tower markers, and obstacle visualization.
 * NO editing - purely visual representation of backend data.
 */
export default function MapViewer({ 
  towers, 
  spans, 
  routeCoordinates, 
  obstacles = [],
  voltage_kv = 220,
  geo_context,
}: MapViewerProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null)
  const markersRef = useRef<any[]>([])
  const routeSourceRef = useRef<string | null>(null)
  const mapboxglRef = useRef<any>(null)

  // "Truth" route line - connects towers directly (tower -> tower -> tower)
  // This proves the line passes through the marker positions
  const routeGeoJSON = useMemo(() => {
    if (!towers || towers.length === 0) return null
    
    const sortedTowers = towers
      .filter(t => t.latitude && t.longitude)
      .sort((a, b) => a.index - b.index)
    
    if (sortedTowers.length < 2) return null
    
    return {
      type: "Feature" as const,
      properties: {},
      geometry: {
        type: "LineString" as const,
        coordinates: sortedTowers.map(t => [t.longitude!, t.latitude!]), // Connects dots perfectly
      },
    }
  }, [towers])

  useEffect(() => {
    // Only initialize if we have coordinates and map isn't already loaded
    if (!towers.length || !towers[0].latitude || !towers[0].longitude) {
      return
    }
    
    // Don't recreate map if it already exists
    if (mapRef.current) {
      return
    }

    // Dynamic import of mapbox-gl
    const loadMap = async () => {
      try {
        const mapboxgl = (await import("mapbox-gl")).default
        
        // Store mapboxgl in ref for use in other useEffect hooks
        mapboxglRef.current = mapboxgl
        
        // Set access token
        if (!mapboxgl.accessToken) {
          mapboxgl.accessToken = "pk.eyJ1Ijoidmlyb2h1bWFuIiwiYSI6ImNtamNyaHIxODByZXAzZHJ6bXZkeWp6cnIifQ.13FV1Zte85JWq-NvrSknnw"
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

        // Add fullscreen control
        map.addControl(new mapboxgl.FullscreenControl(), 'top-right')

        map.on("load", () => {
          // Add "Truth" route polyline - connects towers directly
          if (routeGeoJSON) {
            map.addSource("route", {
              type: "geojson",
              data: routeGeoJSON,
            })
            
            routeSourceRef.current = "route"

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

          // Add obstacle visualization
          obstacles.forEach((obstacle, idx) => {
            if (!obstacle.geometry || obstacle.geometry.length === 0) return

            const obstacleCoords = obstacle.geometry.map(g => [g.lon, g.lat])
            const obstacleType = obstacle.type || 'unknown'
            const obstacleName = obstacle.name || obstacleType

            // Determine color and style based on obstacle type
            let fillColor = '#3b82f6'
            let lineColor = '#3b82f6'
            let lineWidth = 4
            let lineOpacity = 0.6
            let fillOpacity = 0.3
            let lineDasharray: number[] | undefined = undefined

            if (obstacleType === 'river' || obstacleType === 'waterway' || obstacleType === 'water' || obstacleType === 'wetland') {
              fillColor = '#3b82f6'
              lineColor = '#3b82f6'
              lineWidth = 4
              lineOpacity = 0.6
              fillOpacity = 0.3
            } else if (obstacleType === 'highway' || obstacleType === 'road') {
              fillColor = '#f97316'
              lineColor = '#f97316'
              lineWidth = 3
              lineOpacity = 0.8
              fillOpacity = 0.2
              lineDasharray = [2, 4]
            } else if (obstacleType === 'steep_slope') {
              fillColor = '#ef4444'
              lineColor = '#dc2626'
              lineWidth = 2
              lineOpacity = 0.5
              fillOpacity = 0.3
            }

            const isPolygon = obstacleCoords.length > 2 && 
              obstacleCoords[0][0] === obstacleCoords[obstacleCoords.length - 1][0] &&
              obstacleCoords[0][1] === obstacleCoords[obstacleCoords.length - 1][1]

            const sourceId = `obstacle-${idx}`
            const layerId = `obstacle-layer-${idx}`
            const lineLayerId = `obstacle-line-${idx}`

            if (isPolygon) {
              map.addSource(sourceId, {
                type: "geojson",
                data: {
                  type: "Feature",
                  properties: {
                    type: obstacleType,
                    name: obstacleName,
                  },
                  geometry: {
                    type: "Polygon",
                    coordinates: [obstacleCoords],
                  },
                },
              })

              map.addLayer({
                id: layerId,
                type: "fill",
                source: sourceId,
                paint: {
                  "fill-color": fillColor,
                  "fill-opacity": fillOpacity,
                },
              })

              const linePaint: any = {
                "line-color": lineColor,
                "line-width": lineWidth,
                "line-opacity": lineOpacity,
              }
              
              if (lineDasharray !== undefined) {
                linePaint["line-dasharray"] = lineDasharray
              }

              map.addLayer({
                id: lineLayerId,
                type: "line",
                source: sourceId,
                paint: linePaint,
              })
            } else {
              map.addSource(sourceId, {
                type: "geojson",
                data: {
                  type: "Feature",
                  properties: {
                    type: obstacleType,
                    name: obstacleName,
                  },
                  geometry: {
                    type: "LineString",
                    coordinates: obstacleCoords,
                  },
                },
              })

              const linePaint: any = {
                "line-color": lineColor,
                "line-width": lineWidth,
                "line-opacity": lineOpacity,
              }
              
              if (lineDasharray !== undefined) {
                linePaint["line-dasharray"] = lineDasharray
              }

              map.addLayer({
                id: lineLayerId,
                type: "line",
                source: sourceId,
                paint: linePaint,
              })
            }

            // Add hover tooltip
            let currentPopup: any = null
            const showTooltip = (e: any) => {
              if (currentPopup) {
                currentPopup.remove()
                currentPopup = null
              }
              
              const props = e.features[0]?.properties
              if (props && mapboxglRef.current) {
                const tooltip = `${props.name || props.type || 'Obstacle'}`
                const mapboxgl = mapboxglRef.current
                currentPopup = new mapboxgl.Popup({ closeOnClick: true })
                  .setLngLat(e.lngLat)
                  .setHTML(`<strong>${tooltip}</strong><br/>Type: ${props.type || 'unknown'}`)
                  .addTo(map)
              }
            }

            map.on('mouseenter', lineLayerId, () => {
              map.getCanvas().style.cursor = 'pointer'
            })

            map.on('mouseleave', lineLayerId, () => {
              map.getCanvas().style.cursor = ''
            })

            map.on('click', lineLayerId, showTooltip)

            if (isPolygon) {
              map.on('mouseenter', layerId, () => {
                map.getCanvas().style.cursor = 'pointer'
              })

              map.on('mouseleave', layerId, () => {
                map.getCanvas().style.cursor = ''
              })

              map.on('click', layerId, showTooltip)
            }
          })

          // Add tower markers - simple red dots on the line
          // Clear existing markers first
          if (!mapboxglRef.current) return
          const mapboxgl = mapboxglRef.current
          
          markersRef.current.forEach(marker => marker.remove())
          markersRef.current = []
          
          towers.forEach((tower) => {
            if (tower.latitude && tower.longitude) {
              // Create simple red dot marker
              const el = document.createElement("div")
              el.className = "tower-marker"
              el.style.width = "12px"
              el.style.height = "12px"
              el.style.borderRadius = "50%"
              el.style.backgroundColor = "#ef4444"
              el.style.border = "2px solid white"
              el.style.boxShadow = "0 2px 4px rgba(0,0,0,0.3)"
              el.style.cursor = "pointer"
              el.style.pointerEvents = "auto"
              el.style.zIndex = "100" // Ensure markers are visible above the line
              
              let title = `Tower ${tower.index}: ${tower.total_height_m.toFixed(1)}m`
              if (tower.nudge_description) {
                title += `\n${tower.nudge_description}`
              }
              el.title = title

              const marker = new mapboxgl.Marker({
                element: el,
                draggable: false, // Viewer-only: no dragging
                anchor: 'center' as any, // Center of dot is the location
                offset: [0, 0],
              })
                .setLngLat([tower.longitude, tower.latitude])
                .addTo(map)

              // Store marker reference
              markersRef.current.push(marker)

              // If tower was nudged, add badge icon on top of tower
              if (tower.original_distance_m && tower.nudge_description) {
                const badgeEl = document.createElement("div")
                badgeEl.innerHTML = "⚠️"
                badgeEl.style.position = "absolute"
                badgeEl.style.top = "-10px"
                badgeEl.style.right = "-6px"
                badgeEl.style.width = "14px"
                badgeEl.style.height = "14px"
                badgeEl.style.backgroundColor = "#fbbf24"
                badgeEl.style.borderRadius = "50%"
                badgeEl.style.display = "flex"
                badgeEl.style.alignItems = "center"
                badgeEl.style.justifyContent = "center"
                badgeEl.style.fontSize = "9px"
                badgeEl.style.cursor = "pointer"
                badgeEl.style.border = "1px solid white"
                badgeEl.style.boxShadow = "0 1px 2px rgba(0,0,0,0.2)"
                badgeEl.title = tower.nudge_description
                el.appendChild(badgeEl)
              }
            }
          })
        })

        return () => {
          map.remove()
        }
      } catch (error) {
        console.error("Failed to load map:", error)
      }
    }

    loadMap()
  }, []) // Only run once on mount

  // Update markers when towers change
  useEffect(() => {
    if (!mapRef.current || !mapboxglRef.current) return
    
    const map = mapRef.current
    const mapboxgl = mapboxglRef.current
    
    // Clear existing markers
    markersRef.current.forEach(marker => marker.remove())
    markersRef.current = []
    
    // Create new markers for all towers
    towers.forEach((tower) => {
      if (tower.latitude && tower.longitude) {
        const el = document.createElement("div")
        el.className = "tower-marker"
        el.style.width = "12px"
        el.style.height = "12px"
        el.style.borderRadius = "50%"
        el.style.backgroundColor = "#ef4444"
        el.style.border = "2px solid white"
        el.style.boxShadow = "0 2px 4px rgba(0,0,0,0.3)"
        el.style.cursor = "pointer"
        el.style.pointerEvents = "auto"
        el.style.position = "relative"
        
        let title = `Tower ${tower.index}: ${tower.total_height_m.toFixed(1)}m`
        if (tower.nudge_description) {
          title += `\n${tower.nudge_description}`
        }
        el.title = title

        const marker = new mapboxgl.Marker({
          element: el,
          draggable: false,
          anchor: 'center' as any,
          offset: [0, 0],
        })
          .setLngLat([tower.longitude, tower.latitude])
          .addTo(map)

        markersRef.current.push(marker)

        // If tower was nudged, add badge icon
        if (tower.original_distance_m && tower.nudge_description) {
          const badgeEl = document.createElement("div")
          badgeEl.innerHTML = "⚠️"
          badgeEl.style.position = "absolute"
          badgeEl.style.top = "-10px"
          badgeEl.style.right = "-6px"
          badgeEl.style.width = "14px"
          badgeEl.style.height = "14px"
          badgeEl.style.backgroundColor = "#fbbf24"
          badgeEl.style.borderRadius = "50%"
          badgeEl.style.display = "flex"
          badgeEl.style.alignItems = "center"
          badgeEl.style.justifyContent = "center"
          badgeEl.style.fontSize = "9px"
          badgeEl.style.cursor = "pointer"
          badgeEl.style.border = "1px solid white"
          badgeEl.style.boxShadow = "0 1px 2px rgba(0,0,0,0.2)"
          badgeEl.title = tower.nudge_description
          el.appendChild(badgeEl)
        }
      }
    })
  }, [towers])

  // Update route polyline when towers change
  useEffect(() => {
    if (!mapRef.current || !routeSourceRef.current) return
    
    const map = mapRef.current
    const sourceId = routeSourceRef.current

    if (routeGeoJSON) {
      try {
        const source = map.getSource(sourceId) as any
        if (source) {
          source.setData(routeGeoJSON)
        }
      } catch (e) {
        console.debug("Route source not ready:", e)
      }
    }
  }, [routeGeoJSON])

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
      <CardContent className="relative">
        <div ref={mapContainerRef} className="relative w-full h-96 rounded-md overflow-hidden" />
      </CardContent>
    </Card>
  )
}
