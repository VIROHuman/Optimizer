"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"

interface TowerOptimizerFormProps {
  onSubmit?: (data: any) => void
  isLoading?: boolean
}

export default function TowerOptimizerForm({ onSubmit, isLoading = false }: TowerOptimizerFormProps) {
  const [formData, setFormData] = React.useState({
    location: "",
    voltage: "",
    terrain: "",
    wind: "",
    soil: "",
    tower: "suspension", // Default matches original optimizer
    projectLength: "50", // Frontend-only: Project length in km (default 50)
    flags: {
      design_for_higher_wind: false,
      include_ice_load: false,
      conservative_foundation: false,
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate all required fields
    if (!formData.location || !formData.voltage || !formData.terrain || !formData.wind || !formData.soil || !formData.tower) {
      alert("Please fill in all required fields")
      return
    }
    
    // Validate voltage is a valid number
    const voltageNum = Number(formData.voltage)
    if (isNaN(voltageNum) || voltageNum <= 0) {
      alert("Please enter a valid voltage level (e.g., 132, 220, 400, 765)")
      return
    }
    
    // Validate location is not empty after trim
    if (!formData.location.trim()) {
      alert("Please enter a valid project location")
      return
    }
    
    // Validate project length (frontend-only, not sent to backend)
    const projectLengthNum = Number(formData.projectLength)
    if (isNaN(projectLengthNum) || projectLengthNum < 1 || projectLengthNum > 1000) {
      alert("Please enter a valid project length between 1 and 1000 km")
      return
    }
    
    onSubmit?.(formData)
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

  return (
    <Card className="bg-card border-border">
      <CardHeader>
        <CardTitle className="text-foreground">Tower Optimization Parameters</CardTitle>
        <CardDescription>Configure the design parameters for your transmission tower optimization</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Parameters Grid */}
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="location" className="text-foreground">
                Location
              </Label>
              <Input
                id="location"
                placeholder="Enter project location"
                value={formData.location}
                onChange={(e) => updateField("location", e.target.value)}
                className="bg-background border-input"
              />
            </div>

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
              </Label>
              <Select value={formData.terrain} onValueChange={(v) => updateField("terrain", v)}>
                <SelectTrigger className="bg-background border-input">
                  <SelectValue placeholder="Select terrain type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="flat">Flat</SelectItem>
                  <SelectItem value="rolling">Rolling</SelectItem>
                  <SelectItem value="mountainous">Mountainous</SelectItem>
                  <SelectItem value="desert">Desert</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="wind" className="text-foreground">
                Wind Zone
              </Label>
              <Select value={formData.wind} onValueChange={(v) => updateField("wind", v)}>
                <SelectTrigger className="bg-background border-input">
                  <SelectValue placeholder="Select wind zone" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="zone_1">Zone 1 (Low)</SelectItem>
                  <SelectItem value="zone_2">Zone 2 (Moderate)</SelectItem>
                  <SelectItem value="zone_3">Zone 3 (High)</SelectItem>
                  <SelectItem value="zone_4">Zone 4 (Very High)</SelectItem>
                </SelectContent>
              </Select>
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
              />
              <p className="text-xs text-muted-foreground">
                Planning input for line-level metrics (not sent to optimizer)
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
  )
}
