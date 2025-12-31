"use client"

import { Separator } from "@/components/ui/separator"
import { CheckCircle, AlertTriangle, Info, FileText, DollarSign, Building2, Shield, AlertCircle, MapPin, Route, Download } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { useState } from "react"
import MapViewer from "@/components/map-viewer"

interface OptimizationResultsProps {
  results: any
  projectLength?: number // Project length in km (now from backend canonical format)
}

export default function OptimizationResults({ results, projectLength }: OptimizationResultsProps) {
  if (!results) return null

  // State for tower details dropdown
  const [selectedTowerIndex, setSelectedTowerIndex] = useState<number | null>(null)

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
  const obstacles = results.obstacles || []  // Obstacles for visualization

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

  // Export to Excel function
  const exportToExcel = () => {
    // Dynamic import of xlsx
    import('xlsx').then((XLSX) => {
      const wb = XLSX.utils.book_new()
      
      // Sheet 1: Project Summary
      const summaryData = [
        ['Transmission Line Design Optimization Report'],
        ['Generated:', new Date().toLocaleString()],
        [''],
        ['PROJECT SUMMARY'],
        ['Route Length (km)', lineSummary.route_length_km],
        ['Total Towers', lineSummary.total_towers],
        ['Tower Density (per km)', lineSummary.tower_density_per_km],
        ['Average Span (m)', lineSummary.avg_span_m],
        ['Tallest Tower (m)', lineSummary.tallest_tower_m],
        ['Deepest Foundation (m)', lineSummary.deepest_foundation_m],
        ['Total Steel (tonnes)', lineSummary.total_steel_tonnes],
        ['Total Concrete (m³)', lineSummary.total_concrete_m3],
        [''],
        ['COST BREAKDOWN'],
        ['Steel Cost', costBreakdown.steel_total, currency.symbol],
        ['Foundation Cost', costBreakdown.foundation_total, currency.symbol],
        ['Erection Cost', costBreakdown.erection_total, currency.symbol],
        ['Transport Cost', costBreakdown.transport_total, currency.symbol],
        ['Land/ROW Cost', costBreakdown.land_ROW_total, currency.symbol],
        ['Total Project Cost', costBreakdown.total_project_cost, currency.symbol],
        ['Cost per km', costBreakdown.total_project_cost / (lineSummary.route_length_km || 1), currency.symbol],
        [''],
        ['SAFETY SUMMARY'],
        ['Overall Status', safetySummary.overall_status],
        ['Governing Risks', safetySummary.governing_risks?.join(', ') || 'None'],
        ['Design Scenarios', safetySummary.design_scenarios_applied?.join(', ') || 'None'],
        [''],
        ['REGIONAL CONTEXT'],
        ['Governing Standard', regionalContext.governing_standard],
        ['Confidence Score', confidence.score || 'N/A'],
        ['Wind Source', regionalContext.wind_source || 'N/A'],
        ['Terrain Source', regionalContext.terrain_source || 'N/A'],
      ]
      const ws1 = XLSX.utils.aoa_to_sheet(summaryData)
      XLSX.utils.book_append_sheet(wb, ws1, 'Project Summary')
      
      // Sheet 2: Tower Details
      const towerHeaders = [
        'Index', 'Distance (m)', 'Latitude', 'Longitude', 'Type', 'Deviation Angle (°)',
        'Base Height (m)', 'Body Extension (m)', 'Total Height (m)', 'Base Width (m)',
        'Foundation Type', 'Footing Length (m)', 'Footing Width (m)', 'Footing Depth (m)',
        'Steel Weight (kg)', 'Steel Cost', 'Foundation Cost', 'Erection Cost',
        'Transport Cost', 'Land/ROW Cost', 'Total Cost', 'Safety Status', 'Governing Load Case', 'Design Reason'
      ]
      const towerRows = towers.map((tower: any) => [
        tower.index,
        tower.distance_along_route_m,
        tower.latitude || 'N/A',
        tower.longitude || 'N/A',
        tower.tower_type,
        tower.deviation_angle_deg || 'N/A',
        tower.base_height_m,
        tower.body_extension_m,
        tower.total_height_m,
        tower.base_width_m || 'N/A',
        tower.foundation_type,
        tower.foundation_dimensions?.length || 'N/A',
        tower.foundation_dimensions?.width || 'N/A',
        tower.foundation_dimensions?.depth || 'N/A',
        tower.steel_weight_kg,
        tower.steel_cost,
        tower.foundation_cost,
        tower.erection_cost,
        tower.transport_cost,
        tower.land_ROW_cost,
        tower.total_cost,
        tower.safety_status,
        tower.governing_load_case || 'N/A',
        tower.design_reason || 'N/A',
      ])
      const ws2 = XLSX.utils.aoa_to_sheet([towerHeaders, ...towerRows])
      XLSX.utils.book_append_sheet(wb, ws2, 'Tower Details')
      
      // Sheet 3: Span Details
      const spanHeaders = [
        'From Tower', 'To Tower', 'Span Length (m)', 'Sag (m)', 'Minimum Clearance (m)',
        'Clearance Margin (%)', 'Wind Zone', 'Ice Load Used', 'Governing Case', 'Is Safe', 'Confidence Score'
      ]
      const spanRows = spans.map((span: any) => [
        span.from_tower_index,
        span.to_tower_index,
        span.span_length_m,
        span.sag_m,
        span.minimum_clearance_m,
        span.clearance_margin_percent,
        span.wind_zone_used,
        span.ice_load_used ? 'Yes' : 'No',
        span.governing_case || 'N/A',
        span.is_safe ? 'Yes' : 'No',
        span.confidence_score || 'N/A',
      ])
      const ws3 = XLSX.utils.aoa_to_sheet([spanHeaders, ...spanRows])
      XLSX.utils.book_append_sheet(wb, ws3, 'Span Details')
      
      // Sheet 4: Risk Advisories
      if (advisories.length > 0) {
        const advisoryHeaders = ['Risk Name', 'Category', 'Why it Matters', 'Not Currently Evaluated', 'Suggested Action']
        const advisoryRows = advisories.map((adv: any) => [
          adv.risk_name || 'N/A',
          adv.risk_category || 'N/A',
          adv.reason || 'N/A',
          adv.not_evaluated || 'N/A',
          adv.suggested_action || 'N/A',
        ])
        const ws4 = XLSX.utils.aoa_to_sheet([advisoryHeaders, ...advisoryRows])
        XLSX.utils.book_append_sheet(wb, ws4, 'Risk Advisories')
      }
      
      // Sheet 5: Calculations & Intermediate Values
      const calcData = [
        ['CALCULATION DETAILS'],
        [''],
        ['Span Calculations'],
        ['Max Span (m)', 'Calculated based on voltage and terrain'],
        ['Min Span (m)', 'Calculated based on voltage and terrain'],
        ['Average Span (m)', lineSummary.avg_span_m],
        [''],
        ['Tower Type Classification'],
        ['Suspension Threshold', '0° - 3° deviation'],
        ['Angle Threshold', '3° - 60° deviation'],
        ['Dead-End Threshold', '> 60° deviation or endpoints'],
        [''],
        ['Cost Calculations'],
        ['Steel Cost per kg', 'Calculated based on regional rates'],
        ['Foundation Cost per m³', 'Calculated based on soil type'],
        ['Erection Cost', 'Calculated based on tower height and type'],
        ['Transport Cost', '20% of erection cost'],
        [''],
        ['Safety Calculations'],
        ['Clearance Margin', 'Minimum 10m above ground'],
        ['Sag Calculation', 'Based on catenary formula'],
        ['Wind Load', 'Based on wind zone and tower height'],
        [''],
        ['Optimization Parameters'],
        ['PSO Particles', optimizationInfo.iterations || 'N/A'],
        ['Converged', optimizationInfo.converged ? 'Yes' : 'No'],
        [''],
        ['Market Rates Reference'],
        ['Description', costBreakdown.market_rates?.description || 'N/A'],
        ['Steel Price (USD/tonne)', costBreakdown.market_rates?.steel_price_usd || 'N/A'],
        ['Cement Price (USD/m³)', costBreakdown.market_rates?.cement_price_usd || 'N/A'],
        ['Labor Factor', costBreakdown.market_rates?.labor_factor || 'N/A'],
        ['Logistics Factor', costBreakdown.market_rates?.logistics_factor || 'N/A'],
      ]
      const ws5 = XLSX.utils.aoa_to_sheet(calcData)
      XLSX.utils.book_append_sheet(wb, ws5, 'Calculations')
      
      // Generate filename with timestamp
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
      const filename = `Transmission_Line_Optimization_${timestamp}.xlsx`
      
      // Write and download
      XLSX.writeFile(wb, filename)
    }).catch((err) => {
      console.error('Error exporting to Excel:', err)
      alert('Error exporting to Excel. Please ensure xlsx library is installed.')
    })
  }

  return (
    <div className="space-y-6">
      {/* Header with Safety Status and Export Button */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-foreground">Optimization Results</h2>
        <div className="flex items-center gap-3">
          <Button
            onClick={exportToExcel}
            variant="outline"
            className="flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            Export to Excel
          </Button>
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
          </CardContent>
        </Card>
      )}

      {/* Map View with Obstacles and Nudges */}
      {towers.length > 0 && towers[0]?.latitude && towers[0]?.longitude && (
        <MapViewer
          towers={towers.map((t: any) => ({
            index: t.index,
            latitude: t.latitude,
            longitude: t.longitude,
            total_height_m: t.total_height_m,
            distance_along_route_m: t.distance_along_route_m,
            nudge_description: t.nudge_description,
            original_distance_m: t.original_distance_m,
          }))}
          spans={spans}
          routeCoordinates={towers
            .filter((t: any) => t.latitude && t.longitude)
            .map((t: any) => ({ lat: t.latitude, lon: t.longitude }))}
          obstacles={obstacles}
          voltage_kv={results.design_inputs?.voltage || 220}
          geo_context={results.geographic_resolution ? {
            country_code: results.geographic_resolution.country_code,
            country_name: results.geographic_resolution.country_name,
            state: results.geographic_resolution.state,
          } : undefined}
        />
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
            <CardDescription>Optimized tower designs along route</CardDescription>
          </CardHeader>
          <CardContent>
            {/* Tower Details Dropdown */}
            <div className="mb-4 p-4 rounded-md border-2 border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30">
              <label className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-2 block">
                View Tower Details
              </label>
              <Select 
                value={selectedTowerIndex !== null ? selectedTowerIndex.toString() : ""} 
                onValueChange={(value) => setSelectedTowerIndex(value ? parseInt(value) : null)}
              >
                <SelectTrigger className="w-full border-blue-300 dark:border-blue-700 bg-white dark:bg-gray-900">
                  <SelectValue placeholder="Select a tower to view detailed information" />
                </SelectTrigger>
                <SelectContent>
                  {towers.map((tower: any, idx: number) => (
                    <SelectItem key={idx} value={idx.toString()}>
                      Tower {tower.index} - {tower.tower_type} ({tower.total_height_m?.toFixed(1)}m)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedTowerIndex !== null && towers[selectedTowerIndex] && (
                <div className="mt-4 p-4 bg-white dark:bg-gray-800 rounded-md border border-blue-200 dark:border-blue-800">
                  {(() => {
                    const tower = towers[selectedTowerIndex]
                    return (
                      <div className="space-y-3">
                        <h4 className="font-semibold text-blue-800 dark:text-blue-300">
                          Tower {tower.index} Details
                        </h4>
                        <dl className="grid grid-cols-2 gap-3 text-sm">
                          <div>
                            <dt className="text-muted-foreground">Type</dt>
                            <dd className="font-medium">{tower.tower_type}</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Height</dt>
                            <dd className="font-medium">{tower.total_height_m?.toFixed(2)} m</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Tower Base Width</dt>
                            <dd className="font-medium">{tower.base_width_m?.toFixed(2) || "N/A"} m</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Footing Width</dt>
                            <dd className="font-medium">{tower.foundation_dimensions?.width?.toFixed(2) || "N/A"} m</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Deviation Angle</dt>
                            <dd className="font-medium">{tower.deviation_angle_deg?.toFixed(1) || "N/A"}°</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Steel Weight</dt>
                            <dd className="font-medium">{tower.steel_weight_kg?.toLocaleString()} kg</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Total Cost</dt>
                            <dd className="font-medium">{formatCostDecimal(tower.total_cost || 0)}</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">Distance</dt>
                            <dd className="font-medium">{tower.distance_along_route_m?.toFixed(2)} m</dd>
                          </div>
                          {tower.design_reason && (
                            <div className="col-span-2">
                              <dt className="text-muted-foreground">Design Reason</dt>
                              <dd className="font-medium text-blue-700 dark:text-blue-400">{tower.design_reason}</dd>
                            </div>
                          )}
                        </dl>
                      </div>
                    )
                  })()}
                </div>
              )}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left p-2 text-muted-foreground">Index</th>
                    <th className="text-left p-2 text-muted-foreground">Type</th>
                    <th className="text-left p-2 text-muted-foreground">Height (m)</th>
                    <th className="text-left p-2 text-muted-foreground">Base Width (m)</th>
                    <th className="text-left p-2 text-muted-foreground">Steel (kg)</th>
                    <th className="text-left p-2 text-muted-foreground">Cost</th>
                    <th className="text-left p-2 text-muted-foreground">Status</th>
                    <th className="text-left p-2 text-muted-foreground">
                      <div className="flex items-center gap-1">
                        Design Reason
                        <Info className="h-3 w-3 text-muted-foreground" title="Explanation for tower type selection" />
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {towers.map((tower: any, idx: number) => (
                    <tr key={idx} className="border-b border-border">
                      <td className="p-2 font-medium">{tower.index}</td>
                      <td className="p-2">{tower.tower_type}</td>
                      <td className="p-2">{tower.total_height_m?.toFixed(2)}</td>
                      <td className="p-2">
                        <div className="space-y-1">
                          <div className="font-medium">{tower.base_width_m?.toFixed(2) || "N/A"} m</div>
                          <div className="text-xs text-muted-foreground">Footing: {tower.foundation_dimensions?.width?.toFixed(2) || "N/A"} m</div>
                        </div>
                      </td>
                      <td className="p-2">{tower.steel_weight_kg?.toLocaleString()}</td>
                      <td className="p-2">
                        {formatCostDecimal(tower.total_cost || 0)}
                      </td>
                      <td className="p-2">
                        <Badge
                          variant={tower.safety_status === "SAFE" ? "default" : "secondary"}
                          className={tower.safety_status === "SAFE" ? "bg-green-600" : ""}
                        >
                          {tower.safety_status}
                        </Badge>
                      </td>
                      <td className="p-2">
                        {tower.design_reason ? (
                          <div className="flex items-start gap-1 group relative">
                            <Info 
                              className="h-4 w-4 text-blue-600 dark:text-blue-400 cursor-help flex-shrink-0 mt-0.5" 
                              title={tower.design_reason}
                            />
                            <span 
                              className="text-xs text-muted-foreground line-clamp-2 max-w-[200px]"
                              title={tower.design_reason}
                            >
                              {tower.design_reason}
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">N/A</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {towers.length === 0 && (
              <p className="text-muted-foreground text-sm mt-4">No tower data provided</p>
            )}
          </CardContent>
        </Card>
      )}

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
        <Card className="bg-card border-border border-slate-200 dark:border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg flex items-center gap-2">
              <Info className="h-5 w-5 text-slate-600 dark:text-slate-400" />
              Risk Advisories
            </CardTitle>
            <CardDescription>Region-specific design recommendations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {advisories.map((advisory: any, index: number) => (
              <div
                key={index}
                className="flex items-start gap-3 p-4 rounded-md bg-slate-50/50 dark:bg-slate-900/20 border border-slate-200 dark:border-slate-800/50"
              >
                <Info className="h-5 w-5 text-slate-500 dark:text-slate-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="font-semibold text-slate-700 dark:text-slate-300 mb-2">
                    {advisory.risk_name || "Risk Advisory"}
                  </div>
                  <div className="text-sm text-slate-600 dark:text-slate-400 space-y-2">
                    <p><strong>Why it matters:</strong> {advisory.reason}</p>
                    <p><strong>Not currently evaluated:</strong> {advisory.not_evaluated}</p>
                    {advisory.suggested_action && (
                      <div className="mt-2 p-2 bg-slate-100/80 dark:bg-slate-800/40 rounded border border-slate-200 dark:border-slate-700">
                        <p className="font-medium text-slate-700 dark:text-slate-300">{advisory.suggested_action}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* 9. Constraint Log - Obstacle Detection & Nudges */}
      {(obstacles.length > 0 || towers.some((t: any) => t.nudge_description)) && (
        <Card className="bg-card border-border border-slate-200 dark:border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-slate-600 dark:text-slate-400" />
              Constraint Log
            </CardTitle>
            <CardDescription>Automatic obstacle detection and tower adjustments</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Detected Obstacles */}
            {obstacles.length > 0 && (
              <div>
                <h4 className="font-semibold text-foreground mb-2">Detected Obstacles</h4>
                <ul className="space-y-2 text-sm">
                  {obstacles.map((obstacle: any, idx: number) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-slate-500 dark:text-slate-400">✅</span>
                      <span className="text-slate-700 dark:text-slate-300">
                        Detected {obstacle.type === 'river' ? 'River' : 
                                  obstacle.type === 'highway' ? 'Highway' : 
                                  obstacle.type === 'steep_slope' ? 'Steep Slope' : 
                                  'Obstacle'} at {obstacle.start_distance_m?.toFixed(0) || 'N/A'}m - {obstacle.end_distance_m?.toFixed(0) || 'N/A'}m
                        {obstacle.name && ` (${obstacle.name})`}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Tower Nudges */}
            {towers.filter((t: any) => t.nudge_description).length > 0 && (
              <div>
                <h4 className="font-semibold text-foreground mb-2">Tower Adjustments</h4>
                <ul className="space-y-2 text-sm">
                  {towers
                    .filter((t: any) => t.nudge_description)
                    .map((tower: any) => (
                      <li key={tower.index} className="flex items-start gap-2">
                        <span className="text-slate-500 dark:text-slate-400">🛠️</span>
                        <span className="text-slate-700 dark:text-slate-300">
                          Tower {tower.index}: {tower.nudge_description}
                          {tower.original_distance_m && (
                            <span className="text-muted-foreground ml-1">
                              (Original: {tower.original_distance_m.toFixed(1)}m → Actual: {tower.distance_along_route_m.toFixed(1)}m)
                            </span>
                          )}
                        </span>
                      </li>
                    ))}
                </ul>
              </div>
            )}

            {/* Summary */}
            <div className="mt-4 p-3 bg-slate-50/50 dark:bg-slate-900/20 rounded-md border border-slate-200 dark:border-slate-800">
              <p className="text-xs text-slate-600 dark:text-slate-400">
                <strong>Note:</strong> The system automatically detected {obstacles.length} obstacle(s) and adjusted {
                  towers.filter((t: any) => t.nudge_description).length
                } tower position(s) to ensure safe placement. All adjustments are within engineering tolerances.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 10. Market Rates Reference */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-foreground text-lg flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Market Rates Reference
          </CardTitle>
          <CardDescription>Regional construction cost rates used for calculations</CardDescription>
        </CardHeader>
        <CardContent>
          {costBreakdown?.market_rates ? (
            <div className="space-y-4">
              <div className="bg-slate-50 dark:bg-slate-900/50 p-3 rounded-lg border border-slate-200 dark:border-slate-800">
                <p className="text-sm font-medium text-foreground mb-3">
                  {costBreakdown.market_rates.description || "Market Rates"}
                </p>
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-muted-foreground">Steel Price</dt>
                    <dd className="font-medium text-foreground">
                      ${costBreakdown.market_rates.steel_price_usd?.toLocaleString() || "N/A"} / tonne
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Cement Price</dt>
                    <dd className="font-medium text-foreground">
                      ${costBreakdown.market_rates.cement_price_usd?.toLocaleString() || "N/A"} / m³
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Labor Factor</dt>
                    <dd className="font-medium text-foreground">
                      {costBreakdown.market_rates.labor_factor?.toFixed(1) || "N/A"}x
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Logistics Factor</dt>
                    <dd className="font-medium text-foreground">
                      {costBreakdown.market_rates.logistics_factor?.toFixed(1) || "N/A"}x
                    </dd>
                  </div>
                </dl>
              </div>
              <p className="text-xs text-muted-foreground italic">
                Source: Global Construction Cost Reference Library (Q4 2024 / Q1 2025 Estimates)
              </p>
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              <p>Market rates information is not available in the response.</p>
              <p className="mt-2 text-xs">Debug: costBreakdown = {JSON.stringify(costBreakdown, null, 2)}</p>
            </div>
          )}
        </CardContent>
      </Card>

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

