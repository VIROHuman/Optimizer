"use client"

import { Separator } from "@/components/ui/separator"
import { CheckCircle, AlertTriangle, Info, FileText, DollarSign, Building2, Shield, AlertCircle, MapPin, Route, ChevronDown, ChevronUp, TrendingUp } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogClose } from "@/components/ui/dialog"
import React, { useState } from "react"

interface OptimizationResultsProps {
  results: any
  projectLength?: number // Project length in km (now from backend canonical format)
}

export default function OptimizationResults({ results, projectLength }: OptimizationResultsProps) {
  if (!results) return null

  // Canonical format fields
  const towers = results.towers || []
  const spans = results.spans || []
  const lineSummary = results.line_summary || {}
  const costBreakdown = results.cost_breakdown || {}
  const safetySummary = results.safety_summary || {}
  const regionalContext = results.regional_context || {}
  const currency = results.currency || { code: "USD", symbol: "$", label: "USD" } // Fallback to USD if not provided
  const warnings = results.warnings || []
  const advisories = results.advisories || []
  const referenceDataStatus = results.reference_data_status || {}
  const optimizationInfo = results.optimization_info || {}

  // State for tower details expansion and cost driver dialog
  const [expandedTowers, setExpandedTowers] = useState<Set<number>>(new Set())
  const [costDriverDialog, setCostDriverDialog] = useState<{ open: boolean; tower: any | null }>({ open: false, tower: null })

  // Format cost for display (handle Indian Rupees with "Cr" for crores)
  const formatCost = (cost: number) => {
    if (currency.code === "INR" && cost >= 10000000) {
      return `${currency.symbol}${(cost / 10000000).toFixed(1)} Cr`
    }
    return `${currency.symbol}${cost.toLocaleString()}`
  }

  // Format cost with decimals
  const formatCostDecimal = (cost: number) => {
    return `${currency.symbol}${cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  // TASK 5.7: Extract cost context for "Why cost is high" explanation
  const costContext = results.cost_context || {}
  const confidence = regionalContext.confidence || {}
  
  // TASK 5.7: Calculate cost percentages for explanation
  const totalCost = costBreakdown.total_project_cost || 0
  const steelPercent = totalCost > 0 ? ((costBreakdown.steel_total || 0) / totalCost) * 100 : 0
  const foundationPercent = totalCost > 0 ? ((costBreakdown.foundation_total || 0) / totalCost) * 100 : 0
  const landRowPercent = totalCost > 0 ? ((costBreakdown.land_ROW_total || 0) / totalCost) * 100 : 0
  const terrainPercent = 0 // Placeholder - could be calculated from terrain complexity

  // Calculate average tower cost for comparison
  const avgTowerCost = towers.length > 0 
    ? towers.reduce((sum: number, t: any) => sum + (t.total_cost || 0), 0) / towers.length 
    : 0

  // Function to analyze cost drivers for a specific tower
  const analyzeTowerCostDrivers = (tower: any) => {
    const drivers: string[] = []
    const costBreakdown: any = {
      steel: tower.steel_cost || 0,
      foundation: tower.foundation_cost || 0,
      erection: tower.erection_cost || 0,
      transport: tower.transport_cost || 0,
      land: tower.land_ROW_cost || 0,
      total: tower.total_cost || 0,
    }

    // Calculate percentages
    const percentages: any = {}
    if (costBreakdown.total > 0) {
      percentages.steel = (costBreakdown.steel / costBreakdown.total) * 100
      percentages.foundation = (costBreakdown.foundation / costBreakdown.total) * 100
      percentages.erection = (costBreakdown.erection / costBreakdown.total) * 100
      percentages.transport = (costBreakdown.transport / costBreakdown.total) * 100
      percentages.land = (costBreakdown.land / costBreakdown.total) * 100
    }

    // Compare to average
    const costDiff = costBreakdown.total - avgTowerCost
    const costDiffPercent = avgTowerCost > 0 ? (costDiff / avgTowerCost) * 100 : 0

    // Identify why this tower is more/less expensive
    if (costDiffPercent > 10) {
      drivers.push(`This tower is ${Math.abs(costDiffPercent).toFixed(1)}% more expensive than average`)
      
      // Check individual components
      const avgSteelCost = towers.length > 0 
        ? towers.reduce((sum: number, t: any) => sum + (t.steel_cost || 0), 0) / towers.length 
        : 0
      const avgFoundationCost = towers.length > 0 
        ? towers.reduce((sum: number, t: any) => sum + (t.foundation_cost || 0), 0) / towers.length 
        : 0
      const avgErectionCost = towers.length > 0 
        ? towers.reduce((sum: number, t: any) => sum + (t.erection_cost || 0), 0) / towers.length 
        : 0

      if (costBreakdown.steel > avgSteelCost * 1.15) {
        drivers.push(`Steel cost is ${((costBreakdown.steel / avgSteelCost - 1) * 100).toFixed(1)}% above average (likely due to taller height or wider base)`)
      }
      if (costBreakdown.foundation > avgFoundationCost * 1.15) {
        drivers.push(`Foundation cost is ${((costBreakdown.foundation / avgFoundationCost - 1) * 100).toFixed(1)}% above average (likely due to larger footing dimensions)`)
      }
      if (costBreakdown.erection > avgErectionCost * 1.15) {
        drivers.push(`Erection cost is ${((costBreakdown.erection / avgErectionCost - 1) * 100).toFixed(1)}% above average (likely due to complex tower type or difficult access)`)
      }
    } else if (costDiffPercent < -10) {
      drivers.push(`This tower is ${Math.abs(costDiffPercent).toFixed(1)}% less expensive than average`)
    } else {
      drivers.push("This tower's cost is close to the average")
    }

    // Add design-specific drivers
    if (tower.tower_type === "dead_end") {
      drivers.push("Dead-end tower type requires stronger structure (higher steel cost)")
    } else if (tower.tower_type === "angle" || tower.tower_type === "tension") {
      drivers.push("Angle/tension tower type requires additional structural support")
    }

    if (tower.total_height_m > (lineSummary.tallest_tower_m || 0) * 0.9) {
      drivers.push("Taller tower requires more steel and larger foundation")
    }

    if (tower.base_width_m > 12) {
      drivers.push("Wider base width increases steel quantity and foundation size")
    }

    if (tower.foundation_dimensions?.depth > 4) {
      drivers.push("Deeper foundation increases excavation and concrete costs")
    }

    return {
      drivers,
      costBreakdown,
      percentages,
      costDiff,
      costDiffPercent,
    }
  }

  const toggleTowerExpansion = (towerIndex: number) => {
    const newExpanded = new Set(expandedTowers)
    if (newExpanded.has(towerIndex)) {
      newExpanded.delete(towerIndex)
    } else {
      newExpanded.add(towerIndex)
    }
    setExpandedTowers(newExpanded)
  }

  return (
    <div className="space-y-6">
      {/* Header with Safety Status */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-foreground">Optimization Results</h2>
        <Badge
          variant={safetySummary.overall_status === "SAFE" ? "default" : "destructive"}
          className={safetySummary.overall_status === "SAFE" ? "bg-green-600 hover:bg-green-700" : ""}
        >
          {safetySummary.overall_status === "SAFE" ? (
            <CheckCircle className="h-3.5 w-3.5 mr-1" />
          ) : (
            <AlertTriangle className="h-3.5 w-3.5 mr-1" />
          )}
          {safetySummary.overall_status || "UNKNOWN"}
        </Badge>
      </div>

      {/* TASK 5.7: Route Overview Section */}
      {lineSummary.route_length_km > 0 && (
        <Card className="bg-card border-border border-blue-200 dark:border-blue-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg flex items-center gap-2">
              <Route className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              Route Overview
            </CardTitle>
            <CardDescription>Route-level optimization summary</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <dt className="text-sm text-muted-foreground">Route Length</dt>
                <dd className="font-medium text-foreground">{lineSummary.route_length_km?.toFixed(2) || "N/A"} km</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">Tower Count</dt>
                <dd className="font-medium text-foreground">{lineSummary.total_towers || towers.length || "N/A"}</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">Tower Density</dt>
                <dd className="font-medium text-foreground">{lineSummary.tower_density_per_km?.toFixed(2) || "N/A"} /km</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">Avg Span</dt>
                <dd className="font-medium text-foreground">{lineSummary.avg_span_m?.toFixed(0) || "N/A"} m</dd>
              </div>
            </dl>
            {/* Display wind_source and terrain_source if available */}
            {(lineSummary.wind_source || lineSummary.terrain_source) && (
              <div className="mt-4 pt-4 border-t border-border">
                <dl className="grid grid-cols-2 gap-4">
                  {lineSummary.wind_source && (
                    <div>
                      <dt className="text-sm text-muted-foreground">Wind Zone Source</dt>
                      <dd className="font-medium text-foreground">
                        {lineSummary.wind_source === "map-derived" ? (
                          <span className="text-green-600 dark:text-green-400">Map-derived</span>
                        ) : (
                          <span className="text-amber-600 dark:text-amber-400">User-selected</span>
                        )}
                      </dd>
                    </div>
                  )}
                  {lineSummary.terrain_source && (
                    <div>
                      <dt className="text-sm text-muted-foreground">Terrain Source</dt>
                      <dd className="font-medium text-foreground">
                        {lineSummary.terrain_source === "elevation-derived" ? (
                          <span className="text-green-600 dark:text-green-400">Elevation-derived</span>
                        ) : (
                          <span className="text-amber-600 dark:text-amber-400">User-selected</span>
                        )}
                      </dd>
                    </div>
                  )}
                </dl>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* TASK 5.7: "Why cost is high" Explanation */}
      {costContext && totalCost > 0 && (
        <Card className="bg-card border-border border-purple-200 dark:border-purple-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              Cost Context (Indicative)
            </CardTitle>
            <CardDescription>Understanding the primary drivers of the estimated project cost</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Cost per km</dt>
                <dd className="font-medium text-foreground">
                  {formatCost(costContext.cost_per_km || 0)} {currency.label}/km
                </dd>
              </div>
              <div className="pt-2">
                <dt className="text-muted-foreground mb-2">Cost Breakdown:</dt>
                <div className="space-y-2">
                  {landRowPercent > 0 && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Right-of-Way (ROW)</span>
                      <span className="font-medium text-foreground">{landRowPercent.toFixed(1)}%</span>
                    </div>
                  )}
                  {steelPercent > 0 && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Steel Structure</span>
                      <span className="font-medium text-foreground">{steelPercent.toFixed(1)}%</span>
                    </div>
                  )}
                  {foundationPercent > 0 && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Foundation</span>
                      <span className="font-medium text-foreground">{foundationPercent.toFixed(1)}%</span>
                    </div>
                  )}
                </div>
              </div>
              {costContext.primary_drivers && costContext.primary_drivers.length > 0 && (
                <div className="pt-2">
                  <dt className="text-muted-foreground mb-2">Primary Cost Drivers:</dt>
                  <ul className="list-disc list-inside space-y-1">
                    {costContext.primary_drivers.map((driver: string, idx: number) => (
                      <li key={idx} className="text-sm text-foreground">{driver}</li>
                    ))}
                  </ul>
                </div>
              )}
              {costContext.interpretation && (
                <div className="mt-4 p-3 bg-purple-50 dark:bg-purple-950/30 rounded-md border border-purple-200 dark:border-purple-800">
                  <p className="text-sm text-purple-800 dark:text-purple-300">
                    <strong>Interpretation:</strong> {costContext.interpretation}
                  </p>
                </div>
              )}
              {costContext.foundation_uncertainty_note && (
                <div className="mt-3 p-2 bg-amber-50 dark:bg-amber-950/20 rounded-md border border-amber-200 dark:border-amber-800">
                  <p className="text-xs text-amber-700 dark:text-amber-400">
                    <strong>Note:</strong> {costContext.foundation_uncertainty_note}
                  </p>
                </div>
              )}
              {costContext.terrain_contribution_note && (
                <div className="mt-2 p-2 bg-blue-50 dark:bg-blue-950/20 rounded-md border border-blue-200 dark:border-blue-800">
                  <p className="text-xs text-blue-700 dark:text-blue-400">
                    <strong>Note:</strong> {costContext.terrain_contribution_note}
                  </p>
                </div>
              )}
            </dl>
          </CardContent>
        </Card>
      )}

      {/* 1. Regional Context */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-foreground text-lg flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Regional Context
          </CardTitle>
          <CardDescription>Governing standard and regional risk context</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm text-muted-foreground">Governing Standard</dt>
              <dd className="font-medium text-foreground">{regionalContext.governing_standard || "N/A"}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Confidence Score</dt>
              <dd className="font-medium text-foreground">{confidence.score || regionalContext.confidence_score || "N/A"}%</dd>
            </div>
            {regionalContext.wind_source && (
              <div>
                <dt className="text-sm text-muted-foreground">Wind Zone Source</dt>
                <dd className="font-medium text-foreground">
                  {regionalContext.wind_source === "map-derived" ? (
                    <span className="text-green-600 dark:text-green-400">Map-derived</span>
                  ) : (
                    <span className="text-amber-600 dark:text-amber-400">User-selected</span>
                  )}
                </dd>
              </div>
            )}
            {regionalContext.terrain_source && (
              <div>
                <dt className="text-sm text-muted-foreground">Terrain Source</dt>
                <dd className="font-medium text-foreground">
                  {regionalContext.terrain_source === "elevation-derived" ? (
                    <span className="text-green-600 dark:text-green-400">Elevation-derived</span>
                  ) : (
                    <span className="text-amber-600 dark:text-amber-400">User-selected</span>
                  )}
                </dd>
              </div>
            )}
            {confidence.drivers && confidence.drivers.some((d: string) => d.includes("Geographic context derived")) && (
              <div className="col-span-2">
                <dt className="text-sm text-muted-foreground">Location Detection</dt>
                <dd className="font-medium text-foreground text-green-600 dark:text-green-400">
                  <MapPin className="h-4 w-4 inline mr-1" />
                  Auto-detected from route geometry
                </dd>
              </div>
            )}
            {confidence.drivers && confidence.drivers.length > 0 && (
              <div className="col-span-2">
                <dt className="text-sm text-muted-foreground mb-2">Confidence Drivers:</dt>
                <dd className="space-y-1">
                  <ul className="list-disc list-inside space-y-1">
                    {confidence.drivers.map((driver: string, idx: number) => (
                      <li key={idx} className="text-sm text-muted-foreground">{driver}</li>
                    ))}
                  </ul>
                </dd>
              </div>
            )}
            {regionalContext.dominant_regional_risks && regionalContext.dominant_regional_risks.length > 0 && (
              <div className="col-span-2">
                <dt className="text-sm text-muted-foreground mb-2">Dominant Regional Risks</dt>
                <dd className="space-y-1">
                  {regionalContext.dominant_regional_risks.map((risk: string, idx: number) => (
                    <Badge key={idx} variant="outline" className="mr-2">
                      {risk}
                    </Badge>
                  ))}
                </dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>

      {/* 2. Towers Table */}
      {towers.length > 0 && (
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Towers ({towers.length})
            </CardTitle>
            <CardDescription>Optimized tower designs along route. Click info icon to see cost drivers.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left p-2 text-muted-foreground"></th>
                    <th className="text-left p-2 text-muted-foreground">Index</th>
                    <th className="text-left p-2 text-muted-foreground">Type</th>
                    <th className="text-left p-2 text-muted-foreground">Height (m)</th>
                    <th className="text-left p-2 text-muted-foreground">Base Width (m)</th>
                    <th className="text-left p-2 text-muted-foreground">Steel (kg)</th>
                    <th className="text-left p-2 text-muted-foreground">Cost</th>
                    <th className="text-left p-2 text-muted-foreground">Status</th>
                    <th className="text-left p-2 text-muted-foreground">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {towers.map((tower: any, idx: number) => {
                    const isExpanded = expandedTowers.has(tower.index)
                    const costAnalysis = analyzeTowerCostDrivers(tower)
                    return (
                      <React.Fragment key={idx}>
                        {/* Main Tower Row */}
                        <tr className={`
                          border-b border-border/60
                          hover:bg-muted/50
                          transition-colors duration-150
                          ${idx % 2 === 0 ? 'bg-background' : 'bg-muted/20'}
                        `}>
                          <td className="p-3">
                            <button
                              onClick={() => toggleTowerExpansion(tower.index)}
                              className="text-muted-foreground hover:text-foreground transition-colors"
                            >
                              {isExpanded ? (
                                <ChevronUp className="h-4 w-4" />
                              ) : (
                                <ChevronDown className="h-4 w-4" />
                              )}
                            </button>
                          </td>
                          <td className="p-3 font-medium">{tower.index}</td>
                          <td className="p-3">
                            <span className="px-2 py-1 rounded-md bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 text-xs font-medium">
                              {tower.tower_type}
                            </span>
                          </td>
                          <td className="p-3">{tower.total_height_m?.toFixed(2)}</td>
                          <td className="p-3">{tower.base_width_m?.toFixed(2) || "N/A"}</td>
                          <td className="p-3">{tower.steel_weight_kg?.toLocaleString()}</td>
                          <td className="p-3">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold">{formatCostDecimal(tower.total_cost || 0)}</span>
                              <button
                                onClick={() => setCostDriverDialog({ open: true, tower })}
                                className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 transition-colors"
                                title="View cost drivers"
                              >
                                <Info className="h-4 w-4" />
                              </button>
                            </div>
                          </td>
                          <td className="p-3">
                            <Badge
                              variant={tower.safety_status === "SAFE" ? "default" : "secondary"}
                              className={tower.safety_status === "SAFE" ? "bg-green-600" : ""}
                            >
                              {tower.safety_status}
                            </Badge>
                          </td>
                          <td className="p-3">
                            {costAnalysis.costDiffPercent > 10 && (
                              <TrendingUp className="h-4 w-4 text-amber-600" title="Above average cost" />
                            )}
                          </td>
                        </tr>
                        {/* Expanded Details Row */}
                        {isExpanded && (
                          <tr className="border-b-2 border-border/80">
                            <td colSpan={9} className="p-0">
                              <div className="px-6 py-5 bg-gradient-to-br from-muted/40 to-muted/20 border-l-4 border-l-blue-500 dark:border-l-blue-400 shadow-sm">
                                <div className="space-y-4">
                                  {/* Design Parameters Section */}
                                  <div className="pb-3 border-b border-border/50">
                                    <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                                      <Building2 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                                      Design Parameters
                                    </h4>
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                      <div>
                                        <dt className="text-muted-foreground text-xs mb-1">Base Height</dt>
                                        <dd className="font-medium">{tower.base_height_m?.toFixed(2) || "N/A"} m</dd>
                                      </div>
                                      <div>
                                        <dt className="text-muted-foreground text-xs mb-1">Body Extension</dt>
                                        <dd className="font-medium">{tower.body_extension_m?.toFixed(2) || "N/A"} m</dd>
                                      </div>
                                      <div>
                                        <dt className="text-muted-foreground text-xs mb-1">Foundation Type</dt>
                                        <dd className="font-medium">{tower.foundation_type || "N/A"}</dd>
                                      </div>
                                      <div>
                                        <dt className="text-muted-foreground text-xs mb-1">Footing Length</dt>
                                        <dd className="font-medium">{tower.foundation_dimensions?.length?.toFixed(2) || "N/A"} m</dd>
                                      </div>
                                      <div>
                                        <dt className="text-muted-foreground text-xs mb-1">Footing Width</dt>
                                        <dd className="font-medium">{tower.foundation_dimensions?.width?.toFixed(2) || "N/A"} m</dd>
                                      </div>
                                      <div>
                                        <dt className="text-muted-foreground text-xs mb-1">Footing Depth</dt>
                                        <dd className="font-medium">{tower.foundation_dimensions?.depth?.toFixed(2) || "N/A"} m</dd>
                                      </div>
                                      {tower.deviation_angle_deg !== null && tower.deviation_angle_deg !== undefined && (
                                        <div>
                                          <dt className="text-muted-foreground text-xs mb-1">Deviation Angle</dt>
                                          <dd className="font-medium">{tower.deviation_angle_deg.toFixed(1)}°</dd>
                                        </div>
                                      )}
                                      {tower.distance_along_route_m !== null && tower.distance_along_route_m !== undefined && (
                                        <div>
                                          <dt className="text-muted-foreground text-xs mb-1">Distance</dt>
                                          <dd className="font-medium">{(tower.distance_along_route_m / 1000).toFixed(2)} km</dd>
                                        </div>
                                      )}
                                      {tower.governing_load_case && (
                                        <div className="col-span-2">
                                          <dt className="text-muted-foreground text-xs mb-1">Governing Load Case</dt>
                                          <dd className="font-medium text-amber-600 dark:text-amber-400">{tower.governing_load_case}</dd>
                                        </div>
                                      )}
                                      {tower.governing_uplift_case && (
                                        <div className="col-span-2">
                                          <dt className="text-muted-foreground text-xs mb-1">Governing Uplift Case</dt>
                                          <dd className="font-medium text-amber-600 dark:text-amber-400">{tower.governing_uplift_case}</dd>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                  
                                  {/* Cost Breakdown Section */}
                                  <div className="pt-3">
                                    <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                                      <DollarSign className="h-4 w-4 text-green-600 dark:text-green-400" />
                                      Cost Breakdown
                                    </h4>
                                    <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                                      <div className="p-3 rounded-md bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800">
                                        <div className="text-xs text-muted-foreground mb-1">Steel</div>
                                        <div className="font-semibold text-blue-700 dark:text-blue-300">{formatCostDecimal(tower.steel_cost || 0)}</div>
                                        <div className="text-xs text-muted-foreground mt-1">{costAnalysis.percentages.steel?.toFixed(1)}%</div>
                                      </div>
                                      <div className="p-3 rounded-md bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800">
                                        <div className="text-xs text-muted-foreground mb-1">Foundation</div>
                                        <div className="font-semibold text-amber-700 dark:text-amber-300">{formatCostDecimal(tower.foundation_cost || 0)}</div>
                                        <div className="text-xs text-muted-foreground mt-1">{costAnalysis.percentages.foundation?.toFixed(1)}%</div>
                                      </div>
                                      <div className="p-3 rounded-md bg-purple-50 dark:bg-purple-950/20 border border-purple-200 dark:border-purple-800">
                                        <div className="text-xs text-muted-foreground mb-1">Erection</div>
                                        <div className="font-semibold text-purple-700 dark:text-purple-300">{formatCostDecimal(tower.erection_cost || 0)}</div>
                                        <div className="text-xs text-muted-foreground mt-1">{costAnalysis.percentages.erection?.toFixed(1)}%</div>
                                      </div>
                                      <div className="p-3 rounded-md bg-indigo-50 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-800">
                                        <div className="text-xs text-muted-foreground mb-1">Transport</div>
                                        <div className="font-semibold text-indigo-700 dark:text-indigo-300">{formatCostDecimal(tower.transport_cost || 0)}</div>
                                        <div className="text-xs text-muted-foreground mt-1">{costAnalysis.percentages.transport?.toFixed(1)}%</div>
                                      </div>
                                      <div className="p-3 rounded-md bg-teal-50 dark:bg-teal-950/20 border border-teal-200 dark:border-teal-800">
                                        <div className="text-xs text-muted-foreground mb-1">Land/ROW</div>
                                        <div className="font-semibold text-teal-700 dark:text-teal-300">{formatCostDecimal(tower.land_ROW_cost || 0)}</div>
                                        <div className="text-xs text-muted-foreground mt-1">{costAnalysis.percentages.land?.toFixed(1)}%</div>
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                        {/* Spacer row for better visual separation */}
                        {!isExpanded && idx < towers.length - 1 && (
                          <tr>
                            <td colSpan={9} className="h-2 bg-transparent"></td>
                          </tr>
                        )}
                      </React.Fragment>
                    )
                  })}
                </tbody>
              </table>
            </div>
            {towers.length === 0 && (
              <p className="text-muted-foreground text-sm mt-4">No tower data provided</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Cost Driver Dialog */}
      <Dialog open={costDriverDialog.open} onOpenChange={(open) => setCostDriverDialog({ open, tower: null })}>
        <DialogContent>
          <DialogClose onClose={() => setCostDriverDialog({ open: false, tower: null })} />
          {costDriverDialog.tower && (
            <>
              <DialogHeader>
                <DialogTitle>Cost Drivers - Tower {costDriverDialog.tower.index}</DialogTitle>
                <DialogDescription>
                  Analysis of why this tower costs {formatCostDecimal(costDriverDialog.tower.total_cost || 0)}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                {(() => {
                  const analysis = analyzeTowerCostDrivers(costDriverDialog.tower)
                  return (
                    <>
                      <div>
                        <h4 className="font-semibold mb-2">Cost Breakdown</h4>
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Steel:</span>
                            <span className="font-medium">{formatCostDecimal(analysis.costBreakdown.steel)} ({analysis.percentages.steel?.toFixed(1)}%)</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Foundation:</span>
                            <span className="font-medium">{formatCostDecimal(analysis.costBreakdown.foundation)} ({analysis.percentages.foundation?.toFixed(1)}%)</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Erection:</span>
                            <span className="font-medium">{formatCostDecimal(analysis.costBreakdown.erection)} ({analysis.percentages.erection?.toFixed(1)}%)</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Transport:</span>
                            <span className="font-medium">{formatCostDecimal(analysis.costBreakdown.transport)} ({analysis.percentages.transport?.toFixed(1)}%)</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Land/ROW:</span>
                            <span className="font-medium">{formatCostDecimal(analysis.costBreakdown.land)} ({analysis.percentages.land?.toFixed(1)}%)</span>
                          </div>
                          <Separator />
                          <div className="flex justify-between font-semibold">
                            <span>Total:</span>
                            <span>{formatCostDecimal(analysis.costBreakdown.total)}</span>
                          </div>
                        </div>
                      </div>
                      {analysis.costDiffPercent !== 0 && (
                        <div className={`p-3 rounded-md ${analysis.costDiffPercent > 0 ? 'bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800' : 'bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800'}`}>
                          <p className={`text-sm font-medium ${analysis.costDiffPercent > 0 ? 'text-amber-800 dark:text-amber-300' : 'text-green-800 dark:text-green-300'}`}>
                            {analysis.costDiffPercent > 0 ? '↑' : '↓'} {Math.abs(analysis.costDiffPercent).toFixed(1)}% {analysis.costDiffPercent > 0 ? 'above' : 'below'} average tower cost
                          </p>
                        </div>
                      )}
                      <div>
                        <h4 className="font-semibold mb-2">Key Cost Drivers</h4>
                        <ul className="list-disc list-inside space-y-1 text-sm">
                          {analysis.drivers.map((driver, idx) => (
                            <li key={idx} className="text-muted-foreground">{driver}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <h4 className="font-semibold mb-2">Design Parameters</h4>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div>
                            <span className="text-muted-foreground">Type:</span> {costDriverDialog.tower.tower_type}
                          </div>
                          <div>
                            <span className="text-muted-foreground">Height:</span> {costDriverDialog.tower.total_height_m?.toFixed(2)} m
                          </div>
                          <div>
                            <span className="text-muted-foreground">Base Width:</span> {costDriverDialog.tower.base_width_m?.toFixed(2)} m
                          </div>
                          <div>
                            <span className="text-muted-foreground">Steel Weight:</span> {costDriverDialog.tower.steel_weight_kg?.toLocaleString()} kg
                          </div>
                        </div>
                      </div>
                    </>
                  )
                })()}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* 3. Spans Table */}
      {spans.length > 0 && (
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg flex items-center gap-2">
              <Route className="h-5 w-5" />
              Spans ({spans.length})
            </CardTitle>
            <CardDescription>Span details between towers</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left p-2 text-muted-foreground">From</th>
                    <th className="text-left p-2 text-muted-foreground">To</th>
                    <th className="text-left p-2 text-muted-foreground">Length (m)</th>
                    <th className="text-left p-2 text-muted-foreground">Sag (m)</th>
                    <th className="text-left p-2 text-muted-foreground">Clearance (m)</th>
                    <th className="text-left p-2 text-muted-foreground">Margin %</th>
                    <th className="text-left p-2 text-muted-foreground">Wind Zone</th>
                    <th className="text-left p-2 text-muted-foreground">Ice Load</th>
                    <th className="text-left p-2 text-muted-foreground">Safe</th>
                  </tr>
                </thead>
                <tbody>
                  {spans.map((span: any, idx: number) => (
                    <tr key={idx} className="border-b border-border">
                      <td className="p-2 font-medium">T{span.from_tower_index}</td>
                      <td className="p-2 font-medium">T{span.to_tower_index}</td>
                      <td className="p-2">{span.span_length_m?.toFixed(2)}</td>
                      <td className="p-2">{span.sag_m?.toFixed(2)}</td>
                      <td className="p-2">{span.minimum_clearance_m?.toFixed(2)}</td>
                      <td className="p-2">{span.clearance_margin_percent?.toFixed(1)}%</td>
                      <td className="p-2">{span.wind_zone_used || "N/A"}</td>
                      <td className="p-2">{span.ice_load_used ? "Yes" : "No"}</td>
                      <td className="p-2">
                        {span.is_safe ? (
                          <CheckCircle className="h-4 w-4 text-green-600" />
                        ) : (
                          <AlertTriangle className="h-4 w-4 text-red-600" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {spans.length === 0 && (
              <p className="text-muted-foreground text-sm mt-4">No span data provided</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* 4. Line Summary */}
      {lineSummary.route_length_km && (
        <Card className="bg-card border-border border-blue-200 dark:border-blue-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg flex items-center gap-2">
              <Building2 className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              Line-Level Summary
            </CardTitle>
            <CardDescription>Project-level planning metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Route Length</dt>
                <dd className="font-medium text-foreground">{lineSummary.route_length_km?.toFixed(2)} km</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Total Towers</dt>
                <dd className="font-medium text-foreground">{lineSummary.total_towers || "N/A"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Tower Density</dt>
                <dd className="font-medium text-foreground">{lineSummary.tower_density_per_km?.toFixed(2)} towers/km</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Average Span</dt>
                <dd className="font-medium text-foreground">{lineSummary.avg_span_m?.toFixed(2)} m</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Tallest Tower</dt>
                <dd className="font-medium text-foreground">{lineSummary.tallest_tower_m?.toFixed(2)} m</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Deepest Foundation</dt>
                <dd className="font-medium text-foreground">{lineSummary.deepest_foundation_m?.toFixed(2)} m</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Total Steel</dt>
                <dd className="font-medium text-foreground">{lineSummary.total_steel_tonnes?.toFixed(2)} tonnes</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Total Concrete</dt>
                <dd className="font-medium text-foreground">{lineSummary.total_concrete_m3?.toFixed(2)} m³</dd>
              </div>
              <Separator className="my-3" />
              <div className="flex justify-between pt-2">
                <dt className="font-semibold text-foreground">Cost per km</dt>
                <dd className="font-bold text-blue-600 dark:text-blue-400">
                  {formatCostDecimal(lineSummary.cost_per_km || 0)} {currency.label}/km
                </dd>
              </div>
              {lineSummary.total_project_cost && (
                <div className="flex justify-between pt-2">
                  <dt className="font-semibold text-foreground">Total Project Cost</dt>
                  <dd className="font-bold text-blue-600 dark:text-blue-400">
                    {formatCost(lineSummary.total_project_cost || 0)}
                  </dd>
                </div>
              )}
            </dl>
          </CardContent>
        </Card>
      )}

      {/* 5. Cost Breakdown */}
      {costBreakdown.steel_total !== undefined && (
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Cost Breakdown
            </CardTitle>
            <CardDescription>Total project costs by category</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Steel Total</dt>
                <dd className="font-medium text-foreground">
                  {formatCostDecimal(costBreakdown.steel_total || 0)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Foundation Total</dt>
                <dd className="font-medium text-foreground">
                  {formatCostDecimal(costBreakdown.foundation_total || 0)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Erection Total</dt>
                <dd className="font-medium text-foreground">
                  {formatCostDecimal(costBreakdown.erection_total || 0)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Transport Total</dt>
                <dd className="font-medium text-foreground">
                  {formatCostDecimal(costBreakdown.transport_total || 0)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Land/ROW Total</dt>
                <dd className="font-medium text-foreground">
                  {formatCostDecimal(costBreakdown.land_ROW_total || 0)}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      )}

      {/* 6. Safety Summary */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-foreground text-lg flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Safety Summary
          </CardTitle>
          <CardDescription>Overall safety status and governing risks</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Overall Status</dt>
              <dd
                className={`font-semibold ${
                  safetySummary.overall_status === "SAFE" ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                }`}
              >
                {safetySummary.overall_status || "UNKNOWN"}
              </dd>
            </div>
            {safetySummary.governing_risks && safetySummary.governing_risks.length > 0 && (
              <div>
                <dt className="text-muted-foreground mb-2">Governing Risks</dt>
                <dd className="space-y-1">
                  {safetySummary.governing_risks.map((risk: string, idx: number) => (
                    <div key={idx} className="text-sm text-foreground">• {risk}</div>
                  ))}
                </dd>
              </div>
            )}
            {safetySummary.design_scenarios_applied && safetySummary.design_scenarios_applied.length > 0 && (
              <div>
                <dt className="text-muted-foreground mb-2">Design Scenarios Applied</dt>
                <dd className="space-y-1">
                  {safetySummary.design_scenarios_applied.map((scenario: string, idx: number) => (
                    <div key={idx} className="text-sm text-foreground flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                      {scenario}
                    </div>
                  ))}
                </dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>

      {/* 7. Warnings */}
      {warnings.length > 0 && (
        <Card className="bg-card border-border border-amber-200 dark:border-amber-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              Constructability & Practicality Warnings
            </CardTitle>
            <CardDescription>Advisory warnings (not safety violations)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {warnings.map((warning: any, index: number) => (
              <div
                key={index}
                className="flex items-start gap-3 p-3 rounded-md bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800"
              >
                <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="text-sm font-medium text-amber-800 dark:text-amber-300 mb-1">
                    {warning.type === "cost_anomaly" ? "Cost Anomaly" : "Constructability Warning"}
                  </div>
                  <span className="text-sm text-amber-700 dark:text-amber-400">{warning.message || String(warning)}</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* 8. Advisories */}
      {advisories.length > 0 && (
        <Card className="bg-card border-border border-blue-200 dark:border-blue-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg flex items-center gap-2">
              <Info className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              Risk Advisories
            </CardTitle>
            <CardDescription>Region-specific design recommendations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {advisories.map((advisory: any, index: number) => (
              <div
                key={index}
                className="flex items-start gap-3 p-4 rounded-md bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800"
              >
                <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="font-semibold text-blue-800 dark:text-blue-300 mb-2">
                    {advisory.risk_name || "Risk Advisory"}
                  </div>
                  <div className="text-sm text-blue-700 dark:text-blue-400 space-y-2">
                    <p><strong>Why it matters:</strong> {advisory.reason}</p>
                    <p><strong>Not currently evaluated:</strong> {advisory.not_evaluated}</p>
                    {advisory.suggested_action && (
                      <div className="mt-2 p-2 bg-blue-100 dark:bg-blue-900/50 rounded">
                        <p className="font-medium">{advisory.suggested_action}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* 9. Reference Data Status */}
      {referenceDataStatus && Object.keys(referenceDataStatus).length > 0 && (
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg">Reference Data Status</CardTitle>
            <CardDescription>Versioned reference data used in calculations</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-muted-foreground">Cost Indices</dt>
                <dd className="font-medium text-foreground">{referenceDataStatus.cost_index || "N/A"}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Risk Registry</dt>
                <dd className="font-medium text-foreground">{referenceDataStatus.risk_registry || "N/A"}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Code Revision</dt>
                <dd className="font-medium text-foreground">{referenceDataStatus.code_revision || "N/A"}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">FX Reference</dt>
                <dd className="font-medium text-foreground">{referenceDataStatus.currency_rate || "N/A"}</dd>
              </div>
            </dl>
            <p className="text-xs text-muted-foreground mt-4 italic">
              Note: Engineering calculations are NOT automatically modified by live data.
            </p>
          </CardContent>
        </Card>
      )}

      {/* 10. Optimization Metadata */}
      {optimizationInfo && Object.keys(optimizationInfo).length > 0 && (
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg">Optimization Metadata</CardTitle>
            <CardDescription>Optimization method and convergence information</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Optimization Method</dt>
                <dd className="font-medium text-foreground">PSO (Particle Swarm Optimization)</dd>
              </div>
              {optimizationInfo.iterations !== undefined && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Iterations Performed</dt>
                  <dd className="font-medium text-foreground">{optimizationInfo.iterations}</dd>
                </div>
              )}
              {optimizationInfo.converged !== undefined && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Convergence Status</dt>
                  <dd className="font-medium text-foreground">{optimizationInfo.converged ? "Converged" : "Not converged"}</dd>
                </div>
              )}
            </dl>
            <Separator className="my-4" />
            <p className="text-xs text-muted-foreground italic">
              This is a DECISION-SUPPORT TOOL. Final designs must be reviewed by qualified engineers before implementation.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Cost Sensitivity Bands */}
      {costBreakdown.cost_sensitivity && (
        <Card className="bg-card border-border border-purple-200 dark:border-purple-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              Cost Sensitivity Bands
            </CardTitle>
            <CardDescription>Expected cost range with variance</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Lower Bound</dt>
                <dd className="font-medium text-foreground">
                  {formatCostDecimal(results.cost_sensitivity?.lower_bound || 0)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Upper Bound</dt>
                <dd className="font-medium text-foreground">
                  {formatCostDecimal(results.cost_sensitivity?.upper_bound || 0)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Variance</dt>
                <dd className="font-medium text-foreground">
                  ±{results.cost_sensitivity?.variance_percent?.toFixed(1) || "0"}%
                </dd>
              </div>
              <Separator className="my-3" />
              <div className="flex justify-between pt-2">
                <dt className="font-semibold text-foreground">Expected Range</dt>
                <dd className="font-bold text-purple-600 dark:text-purple-400">
                  {results.cost_sensitivity?.expected_range || "N/A"}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      )}

      {/* TASK 5.7: Removed Industry Norm Warnings - replaced with Cost Context */}
      {false && results.industry_norm_warnings && results.industry_norm_warnings.length > 0 && (
        <Card className="bg-card border-border border-orange-200 dark:border-orange-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-orange-600 dark:text-orange-400" />
              Industry Norm Deviations
            </CardTitle>
            <CardDescription>Comparison against Tata/PowerGrid norms</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {results.industry_norm_warnings.map((warning: any, index: number) => (
              <div
                key={index}
                className="flex items-start gap-3 p-3 rounded-md bg-orange-50 dark:bg-orange-950/30 border border-orange-200 dark:border-orange-800"
              >
                <AlertTriangle className="h-5 w-5 text-orange-600 dark:text-orange-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="text-sm font-medium text-orange-800 dark:text-orange-300 mb-1">
                    {warning.metric}: {warning.value}
                  </div>
                  <div className="text-sm text-orange-700 dark:text-orange-400">
                    Industry norm: {warning.norm_range} ({warning.deviation} deviation)
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Confidence Score */}
      {regionalContext.confidence_score !== undefined && (
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg">Confidence Score</CardTitle>
            <CardDescription>Estimate reliability based on assumptions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Confidence</span>
                <div className="flex items-center gap-2">
                  <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full ${
                        regionalContext.confidence_score >= 75
                          ? "bg-green-600"
                          : regionalContext.confidence_score >= 60
                          ? "bg-yellow-600"
                          : "bg-red-600"
                      }`}
                      style={{ width: `${regionalContext.confidence_score}%` }}
                    />
                  </div>
                  <span className="font-semibold">{regionalContext.confidence_score}%</span>
                </div>
              </div>
              {regionalContext.confidence_explanation && (
                <p className="text-sm text-muted-foreground">{regionalContext.confidence_explanation}</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Data Not Provided Warning */}
      {towers.length === 0 && spans.length === 0 && (
        <Card className="bg-card border-border border-red-200 dark:border-red-800">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3 text-red-600 dark:text-red-400">
              <AlertTriangle className="h-5 w-5" />
              <div>
                <p className="font-semibold">DATA NOT PROVIDED</p>
                <p className="text-sm">Backend did not return towers[] or spans[] arrays. This indicates a backend issue.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

    </div>
  )
}

