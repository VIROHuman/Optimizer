"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import RouteMap from "@/components/route-map"
import TerrainSampler from "@/components/terrain-sampler"
import { reverseGeocodeRoute, GeoContext } from "@/lib/mapbox-geocoding"

interface TowerOptimizerFormProps {
  onSubmit?: (data: any) => void
  isLoading?: boolean
}

export default function TowerOptimizerForm({ onSubmit, isLoading = false }: TowerOptimizerFormProps) {
  const [geoContext, setGeoContext] = React.useState<GeoContext | null>(null)
  const [autoDetectedWind, setAutoDetectedWind] = React.useState<string | null>(null)
  const [autoDetectedTerrain, setAutoDetectedTerrain] = React.useState<string | null>(null)
  
  const [formData, setFormData] = React.useState({
    voltage: "",
    terrain: "",
    wind: "",
    soil: "",
    tower: "suspension", // Default matches original optimizer
    projectLength: "50", // Fallback if no route defined
    flags: {
      design_for_higher_wind: false,
      include_ice_load: false,
      conservative_foundation: false,
    },
  })
  
  // Route state (from map)
  const [routeCoordinates, setRouteCoordinates] = React.useState<Array<{ lat: number; lon: number }>>([])
  const [routeLength, setRouteLength] = React.useState<number>(0)
  const [terrainProfile, setTerrainProfile] = React.useState<Array<{ distance_m: number; elevation_m: number }>>([])
  const [mapInstance, setMapInstance] = React.useState<any>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate all required fields (location/wind/terrain optional if route/terrain_profile exist)
    const hasRoute = routeCoordinates.length >= 2
    const hasTerrainProfile = terrainProfile.length >= 2
    const needsLocation = !hasRoute && !formData.location.trim()
    const needsWind = !hasRoute && !formData.wind
    const needsTerrain = !hasTerrainProfile && !formData.terrain
    
    if (needsLocation || needsWind || needsTerrain || !formData.voltage || !formData.soil || !formData.tower) {
      if (needsLocation) {
        alert("Please either draw a route on the map or enter a project location")
      } else if (needsWind) {
        alert("Please either draw a route on the map or select a wind zone")
      } else if (needsTerrain) {
        alert("Please either sample terrain elevation or select a terrain type")
      } else {
        alert("Please fill in all required fields")
      }
      return
    }
    
    // Validate voltage is a valid number
    const voltageNum = Number(formData.voltage)
    if (isNaN(voltageNum) || voltageNum <= 0) {
      alert("Please enter a valid voltage level (e.g., 132, 220, 400, 765)")
      return
    }
    
    // Location validation already handled above (optional if route exists)
    
    // Use route length if available, otherwise use manual input
    const projectLengthNum = routeLength > 0 ? routeLength : Number(formData.projectLength)
    if (isNaN(projectLengthNum) || projectLengthNum < 1 || projectLengthNum > 1000) {
      alert("Please enter a valid project length between 1 and 1000 km, or draw a route on the map")
      return
    }
    
    // Include route data and geo_context in submission
    onSubmit?.({
      ...formData,
      routeCoordinates: routeCoordinates.length > 0 ? routeCoordinates : undefined,
      terrainProfile: terrainProfile.length > 0 ? terrainProfile : undefined,
      projectLength: projectLengthNum,
      geo_context: geoContext || undefined,
    })
  }

  const updateField = (field: string, value: string | boolean) => {
    if (field.startsWith("flags.")) {
      const flagKey = field.replace("flags.", "") as keyof typeof formData.flags
      setFormData((prev) => ({
        ...prev,
        flags: { ...prev.flags, [flagKey]: value as boolean },
      }))
    } else {
      setFormData((prev) => ({ ...prev, [field]: value }))
    }
  }

  const handleRouteComplete = async (route: Array<{ lat: number; lon: number }>, lengthKm: number, map: any) => {
    setRouteCoordinates(route)
    setRouteLength(lengthKm)
    setMapInstance(map)
    // Update project length field
    setFormData(prev => ({ ...prev, projectLength: lengthKm.toFixed(2) }))
    
    // Reverse geocode route to get country and state
    if (route.length > 0) {
      const geo = await reverseGeocodeRoute(route)
      setGeoContext(geo)
      
      // Auto-detect wind zone from location (simplified client-side logic)
      // Note: Full detection happens on backend, this is just for UI preview
      const firstPoint = route[0]
      const lat = firstPoint.lat
      const lon = firstPoint.lon
      
      // Simple heuristics for common regions
      let windZone = "zone_2" // Default
      
      // India coastal regions
      if (lat >= 6.5 && lat <= 37.5 && lon >= 68 && lon <= 97) {
        if (lon < 75.5 || lon > 80.5) {
          windZone = "zone_4" // India coastal
        } else {
          windZone = "zone_2" // India inland
        }
      }
      // USA
      else if (lat >= 24.5 && lat <= 49.5 && lon >= -125 && lon <= -66) {
        windZone = "zone_3" // USA default
      }
      // UAE/Middle East
      else if (lat >= 22 && lat <= 26 && lon >= 51 && lon <= 56) {
        windZone = "zone_4" // UAE
      }
      
      setAutoDetectedWind(windZone)
      // Auto-fill if not already set
      if (!formData.wind) {
        setFormData(prev => ({ ...prev, wind: windZone }))
      }
    }
  }
  
  const handleTerrainComplete = (profile: Array<{ distance_m: number; elevation_m: number }>) => {
    setTerrainProfile(profile)
    
    // Auto-classify terrain from elevation variance
    if (profile.length >= 2) {
      const elevations = profile.map(p => p.elevation_m)
      const minElev = Math.min(...elevations)
      const maxElev = Math.max(...elevations)
      const range = maxElev - minElev
      
      let terrainType = "flat"
      if (range >= 50) {
        terrainType = "mountainous"
      } else if (range >= 10) {
        terrainType = "rolling"
      }
      
      setAutoDetectedTerrain(terrainType)
      // Auto-fill if not already set
      if (!formData.terrain) {
        setFormData(prev => ({ ...prev, terrain: terrainType }))
      }
    }
  }

  return (
    <div className="space-y-6">
      {/* Route Map Section */}
      <RouteMap 
        onRouteComplete={handleRouteComplete}
        onMapReady={setMapInstance}
      />
      
      {/* Terrain Sampler Section */}
      {routeCoordinates.length >= 2 && mapInstance && (
        <TerrainSampler
          routePoints={routeCoordinates}
          mapInstance={mapInstance}
          onTerrainComplete={handleTerrainComplete}
        />
      )}
      
      <Card className="bg-card border-border">
      <CardHeader>
        <CardTitle className="text-foreground">Tower Optimization Parameters</CardTitle>
        <CardDescription>Configure the design parameters for your transmission tower optimization</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Parameters Grid */}
          {/* Geographic Context Display */}
          {routeCoordinates.length >= 2 && geoContext && (
            <div className="p-4 bg-muted rounded-lg border border-border">
              <Label className="text-foreground font-semibold mb-2 block">Geographic Context (Map-Derived)</Label>
              <div className="space-y-1 text-sm">
                {geoContext.country_code ? (
                  <>
                    <div>
                      <span className="text-muted-foreground">Country: </span>
                      <span className="font-medium text-foreground">
                        {geoContext.country_name || geoContext.country_code}
                      </span>
                      {geoContext.country_code && (
                        <span className="text-muted-foreground ml-2">({geoContext.country_code})</span>
                      )}
                    </div>
                    {geoContext.state && (
                      <div>
                        <span className="text-muted-foreground">State/Region: </span>
                        <span className="font-medium text-foreground">{geoContext.state}</span>
                      </div>
                    )}
                    <div>
                      <span className="text-muted-foreground">Resolution: </span>
                      <span className="font-medium text-green-600 dark:text-green-400">
                        {geoContext.resolution_mode === "map-derived" ? "Map-derived" : "Unresolved"}
                      </span>
                    </div>
                  </>
                ) : (
                  <div className="text-amber-600 dark:text-amber-400">
                    ⚠️ Country could not be resolved from coordinates. Using generic physics-only mode.
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="voltage" className="text-foreground">
                Voltage Level (kV)
              </Label>
              <Input
                id="voltage"
                type="number"
                placeholder="e.g., 132, 220, 400, 765"
                min="132"
                step="1"
                value={formData.voltage}
                onChange={(e) => updateField("voltage", e.target.value)}
                className="bg-background border-input"
              />
              <p className="text-xs text-muted-foreground">
                Common values: 132, 220, 400, 765 kV
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="terrain" className="text-foreground">
                Terrain
                {autoDetectedTerrain && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    (Auto-detected from terrain profile)
                  </span>
                )}
              </Label>
              <Select value={formData.terrain} onValueChange={(v) => updateField("terrain", v)}>
                <SelectTrigger className="bg-background border-input">
                  <SelectValue placeholder={autoDetectedTerrain ? `Auto: ${autoDetectedTerrain}` : "Select terrain type"} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="flat">Flat</SelectItem>
                  <SelectItem value="rolling">Rolling</SelectItem>
                  <SelectItem value="mountainous">Mountainous</SelectItem>
                  <SelectItem value="desert">Desert</SelectItem>
                </SelectContent>
              </Select>
              {autoDetectedTerrain && formData.terrain !== autoDetectedTerrain && (
                <p className="text-xs text-amber-600 dark:text-amber-400">
                  Overriding auto-detected terrain ({autoDetectedTerrain})
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="wind" className="text-foreground">
                Wind Zone
                {autoDetectedWind && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    (Auto-detected from route)
                  </span>
                )}
              </Label>
              <Select value={formData.wind} onValueChange={(v) => updateField("wind", v)}>
                <SelectTrigger className="bg-background border-input">
                  <SelectValue placeholder={autoDetectedWind ? `Auto: ${autoDetectedWind}` : "Select wind zone"} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="zone_1">Zone 1 (Low)</SelectItem>
                  <SelectItem value="zone_2">Zone 2 (Moderate)</SelectItem>
                  <SelectItem value="zone_3">Zone 3 (High)</SelectItem>
                  <SelectItem value="zone_4">Zone 4 (Very High)</SelectItem>
                </SelectContent>
              </Select>
              {autoDetectedWind && formData.wind !== autoDetectedWind && (
                <p className="text-xs text-amber-600 dark:text-amber-400">
                  Overriding auto-detected wind zone ({autoDetectedWind})
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="soil" className="text-foreground">
                Soil Type
              </Label>
              <Select value={formData.soil} onValueChange={(v) => updateField("soil", v)}>
                <SelectTrigger className="bg-background border-input">
                  <SelectValue placeholder="Select soil type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="soft">Soft</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="hard">Hard</SelectItem>
                  <SelectItem value="rock">Rock</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="tower" className="text-foreground">
                Tower Type
              </Label>
              <Select value={formData.tower} onValueChange={(v) => updateField("tower", v)}>
                <SelectTrigger className="bg-background border-input">
                  <SelectValue placeholder="Select tower type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="suspension">Suspension</SelectItem>
                  <SelectItem value="angle">Angle</SelectItem>
                  <SelectItem value="tension">Tension</SelectItem>
                  <SelectItem value="dead_end">Dead End</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="projectLength" className="text-foreground">
                Project Length (km)
              </Label>
              <Input
                id="projectLength"
                type="number"
                placeholder="e.g., 50"
                min="1"
                max="1000"
                step="1"
                value={formData.projectLength}
                onChange={(e) => updateField("projectLength", e.target.value)}
                className="bg-background border-input"
                disabled={routeLength > 0}
              />
              <p className="text-xs text-muted-foreground">
                {routeLength > 0 
                  ? `Auto-filled from route: ${routeLength.toFixed(2)} km`
                  : "Optional: Project length for line-level estimates. Draw a route on the map above to auto-fill this."}
              </p>
            </div>
          </div>

          {/* Advanced Options */}
          <div className="space-y-4 pt-4 border-t border-border">
            <h3 className="text-sm font-medium text-foreground">Advanced Options</h3>
            <div className="grid sm:grid-cols-3 gap-4">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="design_for_higher_wind"
                  checked={formData.flags.design_for_higher_wind}
                  onCheckedChange={(checked) => updateField("flags.design_for_higher_wind", !!checked)}
                />
                <Label htmlFor="design_for_higher_wind" className="text-sm text-muted-foreground cursor-pointer">
                  Design for higher wind
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="include_ice_load"
                  checked={formData.flags.include_ice_load}
                  onCheckedChange={(checked) => updateField("flags.include_ice_load", !!checked)}
                />
                <Label htmlFor="include_ice_load" className="text-sm text-muted-foreground cursor-pointer">
                  Include ice load
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="conservative_foundation"
                  checked={formData.flags.conservative_foundation}
                  onCheckedChange={(checked) => updateField("flags.conservative_foundation", !!checked)}
                />
                <Label htmlFor="conservative_foundation" className="text-sm text-muted-foreground cursor-pointer">
                  Conservative foundation
                </Label>
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <div className="pt-4">
            <Button type="submit" disabled={isLoading} className="bg-blue-600 hover:bg-blue-700 text-white">
              {isLoading ? "Running Optimization..." : "Run Optimization"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
    </div>
  )
}
