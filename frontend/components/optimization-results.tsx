"use client"

import { Separator } from "@/components/ui/separator"
import { CheckCircle, AlertTriangle, Info, FileText, DollarSign, Building2, Shield, AlertCircle, MapPin, Route, Download, Loader2, ChevronLeft, ChevronRight, ChevronDown, ChevronUp } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { useState } from "react"
import MapViewer from "@/components/map-viewer"
import { validateFoundationSafety } from "@/lib/api"

interface OptimizationResultsProps {
  results: any
  projectLength?: number // Project length in km (now from backend canonical format)
}

export default function OptimizationResults({ results, projectLength }: OptimizationResultsProps) {
  if (!results) return null

  // State for tower details dropdown
  const [selectedTowerIndex, setSelectedTowerIndex] = useState<number | null>(null)
  
  // State for foundation safety validation
  const [validationResults, setValidationResults] = useState<any>(null)
  const [isValidating, setIsValidating] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [expandedTowers, setExpandedTowers] = useState<Set<number>>(new Set()) // Track which towers are expanded

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

  // Extract project context for validation (try to get from results or use defaults)
  const getProjectLocation = () => {
    if (results.geographic_resolution?.country_name) {
      return results.geographic_resolution.country_name
    }
    return "India" // Default fallback
  }

  const getValidationInputs = () => {
    // Try to extract from results, fallback to defaults
    const voltage = results.design_inputs?.voltage || 400
    const terrain = results.design_inputs?.terrain || "flat"
    const wind = results.design_inputs?.wind || "zone_2"
    const soil = results.design_inputs?.soil || "medium"
    
    return { voltage, terrain, wind, soil }
  }

  // Handle foundation safety validation
  const handleValidateFoundationSafety = async () => {
    setIsValidating(true)
    setValidationError(null)
    
    try {
      const inputs = getValidationInputs()
      const payload = {
        towers: towers,
        project_location: getProjectLocation(),
        voltage: inputs.voltage,
        terrain: inputs.terrain,
        wind: inputs.wind,
        soil: inputs.soil,
        design_for_higher_wind: false,
        include_ice_load: false,
        include_broken_wire: false,
        auto_correct: true,
      }
      
      const validationResult = await validateFoundationSafety(payload)
      setValidationResults(validationResult)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to validate foundation safety"
      setValidationError(errorMessage)
      console.error("Validation error:", err)
    } finally {
      setIsValidating(false)
    }
  }

  // Export safety audit to Excel
  const exportSafetyAuditToExcel = () => {
    if (!validationResults) return
    
    import('xlsx').then((XLSX) => {
      const wb = XLSX.utils.book_new()
      
      // Safety Audit Summary Sheet
      const summaryData = [
        ['Foundation Safety Audit Report'],
        ['Generated:', new Date().toLocaleString()],
        [''],
        ['SUMMARY'],
        ['Uplift Check Passed', `${validationResults.summary.uplift_passed}/${validationResults.summary.total_towers}`],
        ['Sliding Check Passed', `${validationResults.summary.sliding_passed}/${validationResults.summary.total_towers}`],
        ['Overturning Check Passed', `${validationResults.summary.overturning_passed}/${validationResults.summary.total_towers}`],
        ['Total Safety Cost Increase', formatCostDecimal(validationResults.total_safety_cost_increase || 0)],
        [''],
        ['CRITICAL ALERTS'],
      ]
      
      if (validationResults.critical_alerts && validationResults.critical_alerts.length > 0) {
        validationResults.critical_alerts.forEach((alert: any) => {
          summaryData.push([`Tower #${alert.tower_id + 1}`, alert.issues.join('; ')])
        })
      } else {
        summaryData.push(['None', 'All towers passed safety checks'])
      }
      
      const ws1 = XLSX.utils.aoa_to_sheet(summaryData)
      XLSX.utils.book_append_sheet(wb, ws1, 'Summary')
      
      // Tower Safety Details Sheet
      const towerHeaders = [
        'Tower ID', 'Soil Type', 'Status', 'Uplift FOS', 'Sliding FOS', 'Overturning FOS',
        'Original Cost', 'Safety Cost Increase', 'Final Cost', 'Reason'
      ]
      const towerRows = validationResults.tower_results.map((result: any) => {
        const originalCost = result.original_cost || 0
        const safetyIncrease = result.safety_cost_increase || 0
        const finalCost = originalCost + safetyIncrease
        
        // Determine soil type from tower data (if available)
        const tower = towers.find((t: any) => t.index === result.tower_id)
        const soilType = "N/A" // Could be extracted from inputs if stored
        
        return [
          result.tower_id,
          soilType,
          result.status,
          result.uplift_check.fos,
          result.sliding_check.fos,
          result.overturning_check.fos,
          originalCost,
          safetyIncrease,
          finalCost,
          result.reason,
        ]
      })
      
      const ws2 = XLSX.utils.aoa_to_sheet([towerHeaders, ...towerRows])
      
      // Apply conditional formatting (mark FOS < 1.0 in red)
      // Note: xlsx library doesn't support conditional formatting directly
      // This would need to be done in Excel after export or using a more advanced library
      
      XLSX.utils.book_append_sheet(wb, ws2, 'Tower Safety Details')
      
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
      const filename = `Foundation_Safety_Audit_${timestamp}.xlsx`
      
      XLSX.writeFile(wb, filename)
    }).catch((err) => {
      console.error('Error exporting safety audit:', err)
      alert('Error exporting safety audit. Please ensure xlsx library is installed.')
    })
  }

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
        <h2 className="text-2xl font-semibold text-slate-800 dark:text-white">Optimization Results</h2>
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
        <Card className="bg-white dark:bg-black border border-slate-200 dark:border-slate-800 shadow-sm">
          <CardHeader className="pb-3 border-b border-slate-100 dark:border-slate-800 bg-white dark:bg-black">
            <CardTitle className="text-slate-800 dark:text-white text-lg flex items-center gap-2 font-bold">
              <Route className="h-5 w-5 text-[#005EB8] dark:text-blue-400" />
              Route Overview
            </CardTitle>
            <CardDescription className="text-slate-500 dark:text-gray-400">Route-level optimization summary</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <dt className="text-sm text-muted-foreground">Route Length</dt>
                <dd className="font-medium text-slate-800 dark:text-white">{lineSummary.route_length_km?.toFixed(2) || "N/A"} km</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">Tower Count</dt>
                <dd className="font-medium text-slate-800 dark:text-white">{lineSummary.total_towers || towers.length || "N/A"}</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">Tower Density</dt>
                <dd className="font-medium text-slate-800 dark:text-white">{lineSummary.tower_density_per_km?.toFixed(2) || "N/A"} /km</dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">Avg Span</dt>
                <dd className="font-medium text-slate-800 dark:text-white">{lineSummary.avg_span_m?.toFixed(0) || "N/A"} m</dd>
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
            <CardTitle className="text-slate-800 dark:text-white text-lg flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              Cost Context (Indicative)
            </CardTitle>
            <CardDescription>Understanding the primary drivers of the estimated project cost</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Cost per km</dt>
                <dd className="font-medium text-slate-800 dark:text-white">
                  {formatCost(costContext.cost_per_km || 0)}/km
                </dd>
              </div>
              <div className="pt-2">
                <dt className="text-muted-foreground mb-2">Cost Breakdown:</dt>
                <div className="space-y-2">
                  {landRowPercent > 0 && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Right-of-Way (ROW)</span>
                      <span className="font-medium text-slate-800 dark:text-white">{landRowPercent.toFixed(1)}%</span>
                    </div>
                  )}
                  {steelPercent > 0 && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Steel Structure</span>
                      <span className="font-medium text-slate-800 dark:text-white">{steelPercent.toFixed(1)}%</span>
                    </div>
                  )}
                  {foundationPercent > 0 && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Foundation</span>
                      <span className="font-medium text-slate-800 dark:text-white">{foundationPercent.toFixed(1)}%</span>
                    </div>
                  )}
                </div>
              </div>
              {costContext.primary_drivers && costContext.primary_drivers.length > 0 && (
                <div className="pt-2">
                  <dt className="text-muted-foreground mb-2">Primary Cost Drivers:</dt>
                  <ul className="list-disc list-inside space-y-1">
                    {costContext.primary_drivers.map((driver: string, idx: number) => (
                      <li key={idx} className="text-sm text-slate-800 dark:text-white">{driver}</li>
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
          <CardTitle className="text-slate-800 dark:text-white text-lg flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Regional Context
          </CardTitle>
          <CardDescription>Governing standard and regional risk context</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm text-muted-foreground">Governing Standard</dt>
              <dd className="font-medium text-slate-800 dark:text-white">{regionalContext.governing_standard || "N/A"}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Confidence Score</dt>
              <dd className="font-medium text-slate-800 dark:text-white">{confidence.score || regionalContext.confidence_score || "N/A"}%</dd>
            </div>
            {regionalContext.wind_source && (
              <div>
                <dt className="text-sm text-muted-foreground">Wind Zone Source</dt>
                <dd className="font-medium text-slate-800 dark:text-white">
                  {regionalContext.wind_source === "map-derived" ? (
                    <span className="text-green-600 dark:text-green-400">Map-derived</span>
                  ) : (
                    <span className="text-amber-600 ">User-selected</span>
                  )}
                </dd>
              </div>
            )}
            {regionalContext.terrain_source && (
              <div>
                <dt className="text-sm text-muted-foreground">Terrain Source</dt>
                <dd className="font-medium text-slate-800 dark:text-white">
                  {regionalContext.terrain_source === "elevation-derived" ? (
                    <span className="text-green-600 dark:text-green-400">Elevation-derived</span>
                  ) : (
                    <span className="text-amber-600 ">User-selected</span>
                  )}
                </dd>
              </div>
            )}
            {confidence.drivers && confidence.drivers.some((d: string) => d.includes("Geographic context derived")) && (
              <div className="col-span-2">
                <dt className="text-sm text-muted-foreground">Location Detection</dt>
                <dd className="font-medium text-slate-800 dark:text-white text-green-600 dark:text-green-400">
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
        <Card className="bg-white dark:bg-black border border-slate-200 dark:border-slate-800 shadow-sm">
          <CardHeader className="pb-3 border-b border-slate-100 dark:border-slate-800 bg-white dark:bg-black">
            <CardTitle className="text-slate-800 dark:text-white text-lg flex items-center gap-2 font-bold">
              <Building2 className="h-5 w-5" />
              Towers ({towers.length})
            </CardTitle>
            <CardDescription className="text-slate-500 dark:text-gray-400">Optimized tower designs along route</CardDescription>
          </CardHeader>
          <CardContent>
            {/* Tower Details Dropdown with Navigation */}
            <div className="mb-4 p-4 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-black/50">
              <label className="text-sm font-medium text-slate-700 dark:text-gray-200 mb-2 block">
                View Tower Details
              </label>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (selectedTowerIndex !== null && selectedTowerIndex > 0) {
                      setSelectedTowerIndex(selectedTowerIndex - 1)
                    } else if (selectedTowerIndex === null && towers.length > 0) {
                      setSelectedTowerIndex(towers.length - 1)
                    }
                  }}
                  disabled={towers.length === 0}
                  className="flex-shrink-0"
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Select 
                  value={selectedTowerIndex !== null ? selectedTowerIndex.toString() : ""} 
                  onValueChange={(value) => setSelectedTowerIndex(value ? parseInt(value) : null)}
                  className="flex-1"
                >
                  <SelectTrigger className="w-full border-slate-300 dark:border-slate-700 bg-white dark:bg-gray-900 text-slate-900 dark:text-white">
                    <SelectValue placeholder="Select a tower to view detailed information" />
                  </SelectTrigger>
                  <SelectContent>
                    {towers.map((tower: any, idx: number) => (
                      <SelectItem key={idx} value={idx.toString()}>
                        Tower {tower.index + 1} - {tower.tower_type} ({tower.total_height_m?.toFixed(1)}m)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (selectedTowerIndex !== null && selectedTowerIndex < towers.length - 1) {
                      setSelectedTowerIndex(selectedTowerIndex + 1)
                    } else if (selectedTowerIndex === null && towers.length > 0) {
                      setSelectedTowerIndex(0)
                    }
                  }}
                  disabled={towers.length === 0}
                  className="flex-shrink-0"
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
              {selectedTowerIndex !== null && towers.length > 0 && (
                <div className="mt-2 text-xs text-muted-foreground text-center">
                  Tower {selectedTowerIndex + 1} of {towers.length}
                </div>
              )}
              {selectedTowerIndex !== null && towers[selectedTowerIndex] && (
                <div className="mt-4 p-4 bg-white dark:bg-black rounded-md border border-slate-200 dark:border-slate-800">
                  {(() => {
                    const tower = towers[selectedTowerIndex]
                    return (
                      <div className="space-y-3">
                        <h4 className="font-semibold text-slate-800 dark:text-white">
                          Tower {tower.index + 1} Details
                        </h4>
                        {/* Structural Geometry Validation Section */}
                        {(tower.original_height_m || tower.original_base_width_m) && (
                          <div className="mb-4 p-3 rounded-md border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20">
                            <h5 className="font-medium text-sm mb-2 text-amber-800 dark:text-amber-200 flex items-center gap-2">
                              <Building2 className="h-4 w-4" />
                              Structural Geometry Validation
                            </h5>
                            {tower.original_height_m && tower.total_height_m > tower.original_height_m && (
                              <div className="text-xs space-y-1 mb-2">
                                <div className="flex items-center justify-between">
                                  <span className="text-slate-600 dark:text-gray-300">Height (Vertical Clearance):</span>
                                  <div className="flex items-center gap-2">
                                    <span className="text-slate-400 dark:text-gray-500 line-through">{tower.original_height_m.toFixed(2)}m</span>
                                    <span className="text-slate-400 dark:text-gray-500">→</span>
                                    <span className="font-semibold text-amber-700 dark:text-amber-300">{tower.total_height_m.toFixed(2)}m</span>
                                    <span className="text-amber-600 dark:text-amber-300">(+{(tower.total_height_m - tower.original_height_m).toFixed(2)}m)</span>
                                  </div>
                                </div>
                                <div className="text-slate-500 dark:text-gray-400 text-xs pl-4">
                                  Reason: Increased for vertical clearance (wire sag)
                                </div>
                              </div>
                            )}
                            {tower.original_base_width_m && tower.base_width_m > tower.original_base_width_m && (
                              <div className="text-xs space-y-1">
                                <div className="flex items-center justify-between">
                                  <span className="text-slate-600 dark:text-gray-300">Base Width (Slenderness):</span>
                                  <div className="flex items-center gap-2">
                                    <span className="text-slate-400 dark:text-gray-500 line-through">{tower.original_base_width_m.toFixed(2)}m</span>
                                    <span className="text-slate-400 dark:text-gray-500">→</span>
                                    <span className="font-semibold text-amber-700 dark:text-amber-300">{tower.base_width_m.toFixed(2)}m</span>
                                    <span className="text-amber-600 dark:text-amber-300">(+{(tower.base_width_m - tower.original_base_width_m).toFixed(2)}m)</span>
                                  </div>
                                </div>
                                <div className="text-slate-500 dark:text-gray-400 text-xs pl-4">
                                  Reason: Widened for structural stability (1:6 ratio)
                                </div>
                              </div>
                            )}
                            {tower.validation_adjustments && tower.validation_adjustments.length > 0 && (
                              <div className="mt-2 pt-2 border-t border-amber-200 dark:border-amber-800">
                                <div className="text-xs text-slate-600 dark:text-gray-300">
                                  <strong>Adjustments:</strong>
                                  <ul className="list-disc list-inside mt-1 space-y-0.5">
                                    {tower.validation_adjustments.map((adj: string, idx: number) => (
                                      <li key={idx}>{adj}</li>
                                    ))}
                                  </ul>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                        <dl className="grid grid-cols-2 gap-3 text-sm">
                          <div>
                            <dt className="text-slate-500 dark:text-gray-400">Type</dt>
                            <dd className="font-medium text-slate-800 dark:text-white">{tower.tower_type}</dd>
                          </div>
                          <div>
                            <dt className="text-slate-500 dark:text-gray-400">Height</dt>
                            <dd className="font-medium text-slate-800 dark:text-white">
                              {tower.total_height_m?.toFixed(2)} m
                              {tower.original_height_m && tower.total_height_m > tower.original_height_m && (
                                <span className="ml-2 text-xs text-amber-600 dark:text-amber-300">
                                  (Adjusted from {tower.original_height_m.toFixed(2)}m)
                                </span>
                              )}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-slate-500 dark:text-gray-400">Tower Base Width</dt>
                            <dd className="font-medium text-slate-800 dark:text-white">
                              {tower.base_width_m?.toFixed(2) || "N/A"} m
                              {tower.original_base_width_m && tower.base_width_m > tower.original_base_width_m && (
                                <span className="ml-2 text-xs text-amber-600 dark:text-amber-300">
                                  (Adjusted from {tower.original_base_width_m.toFixed(2)}m)
                                </span>
                              )}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-slate-500 dark:text-gray-400">Footing Width</dt>
                            <dd className="font-medium text-slate-800 dark:text-white">{tower.foundation_dimensions?.width?.toFixed(2) || "N/A"} m</dd>
                          </div>
                          <div>
                            <dt className="text-slate-500 dark:text-gray-400">Deviation Angle</dt>
                            <dd className="font-medium text-slate-800 dark:text-white">{tower.deviation_angle_deg?.toFixed(1) || "N/A"}°</dd>
                          </div>
                          <div>
                            <dt className="text-slate-500 dark:text-gray-400">Steel Weight</dt>
                            <dd className="font-medium text-slate-800 dark:text-white">{tower.steel_weight_kg?.toLocaleString()} kg</dd>
                          </div>
                          <div>
                            <dt className="text-slate-500 dark:text-gray-400">Total Cost</dt>
                            <dd className="font-medium text-slate-800 dark:text-white">{formatCostDecimal(tower.total_cost || 0)}</dd>
                          </div>
                          <div>
                            <dt className="text-slate-500 dark:text-gray-400">Distance</dt>
                            <dd className="font-medium text-slate-800 dark:text-white">{tower.distance_along_route_m?.toFixed(2)} m</dd>
                          </div>
                          {tower.design_reason && (
                            <div className="col-span-2">
                              <dt className="text-slate-500 dark:text-gray-400">Design Reason</dt>
                              <dd className="font-medium text-[#005EB8] dark:text-blue-400">{tower.design_reason}</dd>
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
                      <td className="p-2 font-medium">{tower.index + 1}</td>
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
            <CardTitle className="text-slate-800 dark:text-white text-lg flex items-center gap-2">
              <Route className="h-5 w-5" />
              Spans ({spans.length})
            </CardTitle>
            <CardDescription>Span details between towers</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-black">
                    <th className="text-left p-2 text-slate-600 dark:text-gray-300 font-semibold text-xs uppercase">From</th>
                    <th className="text-left p-2 text-slate-600 dark:text-gray-300 font-semibold text-xs uppercase">To</th>
                    <th className="text-left p-2 text-slate-600 dark:text-gray-300 font-semibold text-xs uppercase">Length (m)</th>
                    <th className="text-left p-2 text-slate-600 dark:text-gray-300 font-semibold text-xs uppercase">Sag (m)</th>
                    <th className="text-left p-2 text-slate-600 dark:text-gray-300 font-semibold text-xs uppercase">Clearance (m)</th>
                    <th className="text-left p-2 text-slate-600 dark:text-gray-300 font-semibold text-xs uppercase">Margin %</th>
                    <th className="text-left p-2 text-slate-600 dark:text-gray-300 font-semibold text-xs uppercase">Safe</th>
                  </tr>
                </thead>
                <tbody>
                  {spans.map((span: any, idx: number) => (
                    <tr key={idx} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-gray-900/50">
                      <td className="p-2 font-medium">T{span.from_tower_index + 1}</td>
                      <td className="p-2 font-medium">T{span.to_tower_index + 1}</td>
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
            <CardTitle className="text-slate-800 dark:text-white text-lg flex items-center gap-2">
              <Building2 className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              Line-Level Summary
            </CardTitle>
            <CardDescription>Project-level planning metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Route Length</dt>
                <dd className="font-medium text-slate-800 dark:text-white">{lineSummary.route_length_km?.toFixed(2)} km</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Total Towers</dt>
                <dd className="font-medium text-slate-800 dark:text-white">{lineSummary.total_towers || "N/A"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Tower Density</dt>
                <dd className="font-medium text-slate-800 dark:text-white">{lineSummary.tower_density_per_km?.toFixed(2)} towers/km</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Average Span</dt>
                <dd className="font-medium text-slate-800 dark:text-white">{lineSummary.avg_span_m?.toFixed(2)} m</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Tallest Tower</dt>
                <dd className="font-medium text-slate-800 dark:text-white">{lineSummary.tallest_tower_m?.toFixed(2)} m</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Deepest Foundation</dt>
                <dd className="font-medium text-slate-800 dark:text-white">{lineSummary.deepest_foundation_m?.toFixed(2)} m</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Total Steel</dt>
                <dd className="font-medium text-slate-800 dark:text-white">{lineSummary.total_steel_tonnes?.toFixed(2)} tonnes</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Total Concrete</dt>
                <dd className="font-medium text-slate-800 dark:text-white">{lineSummary.total_concrete_m3?.toFixed(2)} m³</dd>
              </div>
              <Separator className="my-3" />
              <div className="flex justify-between pt-2">
                <dt className="font-semibold text-slate-800 dark:text-white">Cost per km</dt>
                <dd className="font-bold text-blue-600 dark:text-blue-400">
                  {formatCostDecimal(lineSummary.cost_per_km || 0)}/km
                </dd>
              </div>
              {lineSummary.total_project_cost && (
                <div className="flex justify-between pt-2">
                  <dt className="font-semibold text-slate-800 dark:text-white">Total Project Cost</dt>
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
            <CardTitle className="text-slate-800 dark:text-white text-lg flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Cost Breakdown
            </CardTitle>
            <CardDescription>Total project costs by category</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Steel Total</dt>
                <dd className="font-medium text-slate-800 dark:text-white">
                  {formatCostDecimal(costBreakdown.steel_total || 0)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Foundation Total</dt>
                <dd className="font-medium text-slate-800 dark:text-white">
                  {formatCostDecimal(costBreakdown.foundation_total || 0)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Erection Total</dt>
                <dd className="font-medium text-slate-800 dark:text-white">
                  {formatCostDecimal(costBreakdown.erection_total || 0)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Transport Total</dt>
                <dd className="font-medium text-slate-800 dark:text-white">
                  {formatCostDecimal(costBreakdown.transport_total || 0)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Land/ROW Total</dt>
                <dd className="font-medium text-slate-800 dark:text-white">
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
          <CardTitle className="text-slate-800 dark:text-white text-lg flex items-center gap-2">
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
                    <div key={idx} className="text-sm text-slate-800 dark:text-white">• {risk}</div>
                  ))}
                </dd>
              </div>
            )}
            {safetySummary.design_scenarios_applied && safetySummary.design_scenarios_applied.length > 0 && (
              <div>
                <dt className="text-muted-foreground mb-2">Design Scenarios Applied</dt>
                <dd className="space-y-1">
                  {safetySummary.design_scenarios_applied.map((scenario: string, idx: number) => (
                    <div key={idx} className="text-sm text-slate-800 dark:text-white flex items-center gap-2">
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

      {/* Foundation Safety Validation Section */}
      <Card className="bg-white dark:bg-black border border-slate-200 dark:border-slate-800 shadow-sm">
        <CardHeader className="pb-3 border-b border-slate-100 dark:border-slate-800 bg-white dark:bg-black">
          <CardTitle className="text-slate-800 dark:text-white text-lg flex items-center gap-2 font-bold">
            <Shield className="h-5 w-5 text-[#005EB8] dark:text-blue-400" />
            Foundation Safety Validation
          </CardTitle>
          <CardDescription className="text-slate-500 dark:text-gray-400">Post-optimization safety audit for uplift, sliding, and overturning</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!validationResults && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Validate all towers for foundation stability (Uplift, Sliding, Overturning)
              </p>
              <Button
                onClick={handleValidateFoundationSafety}
                disabled={isValidating || towers.length === 0}
                className="flex items-center gap-2 bg-[#005EB8] dark:bg-blue-600 hover:bg-blue-700 dark:hover:bg-blue-700 text-white shadow-sm"
              >
                {isValidating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Validating...
                  </>
                ) : (
                  <>
                    <Shield className="h-4 w-4" />
                    Validate Structural Safety
                  </>
                )}
              </Button>
            </div>
          )}

          {validationError && (
            <div className="p-3 rounded-md bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800">
              <p className="text-sm text-red-600 dark:text-red-400">{validationError}</p>
            </div>
          )}

          {validationResults && (
            <div className="space-y-4">
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 shadow-sm">
                  <CardContent className="pt-4">
                    <div className="text-sm text-slate-600 dark:text-gray-300 mb-1 font-medium">Uplift Check</div>
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {validationResults.summary.uplift_passed}/{validationResults.summary.total_towers} Passed
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 shadow-sm">
                  <CardContent className="pt-4">
                    <div className="text-sm text-slate-600 dark:text-gray-300 mb-1 font-medium">Sliding Check</div>
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {validationResults.summary.sliding_passed}/{validationResults.summary.total_towers} Passed
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 shadow-sm">
                  <CardContent className="pt-4">
                    <div className="text-sm text-slate-600 dark:text-gray-300 mb-1 font-medium">Overturning Check</div>
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {validationResults.summary.overturning_passed}/{validationResults.summary.total_towers} Passed
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Detailed Tower-by-Tower Comparison */}
              <Card className="bg-white dark:bg-black border border-slate-200 dark:border-slate-800 shadow-sm">
                <CardHeader className="pb-3 border-b border-slate-100 dark:border-slate-800 bg-white dark:bg-black">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-slate-800 dark:text-white text-base flex items-center gap-2 font-bold">
                        <FileText className="h-4 w-4" />
                        Detailed Validation Results
                      </CardTitle>
                      <CardDescription className="text-slate-500 dark:text-gray-400">Original vs Adjusted values with safety margins</CardDescription>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (expandedTowers.size === validationResults.tower_results.length) {
                          setExpandedTowers(new Set())
                        } else {
                          setExpandedTowers(new Set(validationResults.tower_results.map((r: any) => r.tower_id)))
                        }
                      }}
                      className="flex items-center gap-2"
                    >
                      {expandedTowers.size === validationResults.tower_results.length ? (
                        <>
                          <ChevronUp className="h-4 w-4" />
                          Collapse All
                        </>
                      ) : (
                        <>
                          <ChevronDown className="h-4 w-4" />
                          Expand All
                        </>
                      )}
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {validationResults.tower_results.map((result: any, idx: number) => {
                      const tower = towers.find((t: any) => t.index === result.tower_id) || towers[idx]
                      const originalDims = tower?.foundation_dimensions || {}
                      const adjustedDims = result.adjusted_dimensions || originalDims
                      const wasAdjusted = result.status === "ADJUSTED" || result.status === "REQUIRES_PILING"
                      const isExpanded = expandedTowers.has(result.tower_id) // Check if this tower is expanded
                      
                      // Calculate safety margins (how much above 1.5 FOS - MIN_FOS)
                      const upliftMargin = result.uplift_check.fos - 1.5
                      const slidingMargin = result.sliding_check.fos - 1.5
                      const overturningMargin = result.overturning_check.fos - 1.5
                      
                      return (
                        <div
                          key={result.tower_id}
                          className={`p-4 rounded-lg border ${
                            result.status === "FAIL" || result.status === "REQUIRES_PILING"
                              ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
                              : result.status === "ADJUSTED"
                              ? "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800"
                              : "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
                          }`}
                        >
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2 flex-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  const newExpanded = new Set(expandedTowers)
                                  if (newExpanded.has(result.tower_id)) {
                                    newExpanded.delete(result.tower_id)
                                  } else {
                                    newExpanded.add(result.tower_id)
                                  }
                                  setExpandedTowers(newExpanded)
                                }}
                                className="h-6 w-6 p-0"
                              >
                                {isExpanded ? (
                                  <ChevronUp className="h-4 w-4" />
                                ) : (
                                  <ChevronDown className="h-4 w-4" />
                                )}
                              </Button>
                              <h4 className="font-semibold text-slate-800 dark:text-white">
                                Tower #{result.tower_id + 1} - {tower?.tower_type || "N/A"}
                              </h4>
                            </div>
                            <Badge
                              className={
                                result.status === "PASS" || result.status === "SAFE"
                                  ? "bg-green-600 dark:bg-green-700 hover:bg-green-700 dark:hover:bg-green-800 text-white"
                                  : result.status === "ADJUSTED"
                                  ? "bg-amber-600 dark:bg-amber-700 hover:bg-amber-700 dark:hover:bg-amber-800 text-white"
                                  : result.status === "REQUIRES_PILING" || result.status === "FAIL"
                                  ? "bg-red-600 dark:bg-red-700 hover:bg-red-700 dark:hover:bg-red-800 text-white"
                                  : "bg-slate-600 dark:bg-slate-700 text-white"
                              }
                            >
                              {result.status === "REQUIRES_PILING" ? "REQUIRES PILING" : result.status}
                            </Badge>
                          </div>
                          
                          {!isExpanded && (
                            <div className="text-sm text-slate-500 dark:text-gray-400">
                              Click to expand details...
                            </div>
                          )}
                          
                          {isExpanded && (
                            <>
                          {/* Structural Geometry Validation Section */}
                          {(tower.original_height_m || tower.original_base_width_m) && (
                            <div className="mb-4 p-3 rounded-md border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20">
                              <h5 className="font-medium text-sm mb-2 text-amber-800 dark:text-amber-200 flex items-center gap-2">
                                <Building2 className="h-4 w-4" />
                                Structural Geometry Check
                              </h5>
                              {tower.original_height_m && tower.total_height_m > tower.original_height_m && (
                                <div className="text-xs space-y-1 mb-2">
                                  <div className="flex items-center justify-between">
                                    <span className="text-slate-600 dark:text-gray-300">Height (Vertical Clearance):</span>
                                    <div className="flex items-center gap-2">
                                      <span className="text-slate-400 dark:text-gray-500 line-through">{tower.original_height_m.toFixed(2)}m</span>
                                      <span className="text-slate-400 dark:text-gray-500">→</span>
                                      <span className="font-semibold text-amber-700 dark:text-amber-400">{tower.total_height_m.toFixed(2)}m</span>
                                      <span className="text-amber-600 dark:text-amber-400">(+{(tower.total_height_m - tower.original_height_m).toFixed(2)}m)</span>
                                    </div>
                                  </div>
                                  <div className="text-slate-500 dark:text-gray-400 text-xs pl-4">
                                    Reason: Prevention of wire-ground contact (sag clearance)
                                  </div>
                                </div>
                              )}
                              {tower.original_base_width_m && tower.base_width_m > tower.original_base_width_m && (
                                <div className="text-xs space-y-1">
                                  <div className="flex items-center justify-between">
                                    <span className="text-slate-600 dark:text-gray-300">Base Width (Slenderness):</span>
                                    <div className="flex items-center gap-2">
                                      <span className="text-slate-400 dark:text-gray-500 line-through">{tower.original_base_width_m.toFixed(2)}m</span>
                                      <span className="text-slate-400 dark:text-gray-500">→</span>
                                      <span className="font-semibold text-amber-700 dark:text-amber-400">{tower.base_width_m.toFixed(2)}m</span>
                                      <span className="text-amber-600 dark:text-amber-400">(+{(tower.base_width_m - tower.original_base_width_m).toFixed(2)}m)</span>
                                    </div>
                                  </div>
                                  <div className="text-slate-500 dark:text-gray-400 text-xs pl-4">
                                    Reason: Prevention of structural buckling (1:6 Ratio)
                                  </div>
                                </div>
                              )}
                              {tower.validation_adjustments && tower.validation_adjustments.length > 0 && (
                                <div className="mt-2 pt-2 border-t border-amber-200 dark:border-amber-800">
                                  <div className="text-xs text-slate-600 dark:text-gray-300">
                                    <strong>Adjustments Made:</strong>
                                    <ul className="list-disc list-inside mt-1 space-y-0.5">
                                      {tower.validation_adjustments.map((adj: string, idx: number) => (
                                        <li key={idx}>{adj}</li>
                                      ))}
                                    </ul>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Foundation Dimensions Comparison */}
                          {wasAdjusted && (
                            <div className="mb-4 p-3 bg-white dark:bg-black rounded-md border border-slate-200 dark:border-slate-800">
                              <h5 className="font-medium text-sm mb-2 text-slate-800 dark:text-white">Foundation Dimensions</h5>
                              <div className="grid grid-cols-3 gap-3 text-sm">
                                <div>
                                  <div className="text-slate-500 dark:text-gray-400 mb-1">Length (m)</div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-slate-800 dark:text-white">{originalDims.length?.toFixed(2) || "N/A"}</span>
                                    {wasAdjusted && (
                                      <>
                                        <span className="text-slate-400 dark:text-gray-500">→</span>
                                        <span className="font-semibold text-amber-600 dark:text-amber-400">
                                          {adjustedDims.length?.toFixed(2)}
                                        </span>
                                        <span className="text-xs text-slate-500 dark:text-gray-400">
                                          (+{((adjustedDims.length || 0) - (originalDims.length || 0)).toFixed(2)}m)
                                        </span>
                                      </>
                                    )}
                                  </div>
                                </div>
                                <div>
                                  <div className="text-slate-500 dark:text-gray-400 mb-1">Width (m)</div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-slate-800 dark:text-white">{originalDims.width?.toFixed(2) || "N/A"}</span>
                                    {wasAdjusted && (
                                      <>
                                        <span className="text-slate-400 dark:text-gray-500">→</span>
                                        <span className="font-semibold text-amber-600 dark:text-amber-400">
                                          {adjustedDims.width?.toFixed(2)}
                                        </span>
                                        <span className="text-xs text-slate-500 dark:text-gray-400">
                                          (+{((adjustedDims.width || 0) - (originalDims.width || 0)).toFixed(2)}m)
                                        </span>
                                      </>
                                    )}
                                  </div>
                                </div>
                                <div>
                                  <div className="text-slate-500 dark:text-gray-400 mb-1">Depth (m)</div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-slate-800 dark:text-white">{originalDims.depth?.toFixed(2) || "N/A"}</span>
                                    {wasAdjusted && (
                                      <>
                                        <span className="text-slate-400 dark:text-gray-500">→</span>
                                        <span className="font-semibold text-amber-600 dark:text-amber-400">
                                          {adjustedDims.depth?.toFixed(2)}
                                        </span>
                                        <span className="text-xs text-slate-500 dark:text-gray-400">
                                          (+{((adjustedDims.depth || 0) - (originalDims.depth || 0)).toFixed(2)}m)
                                        </span>
                                      </>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Safety Checks with Detailed Comparison */}
                          <div className="space-y-3">
                            {/* Uplift Check */}
                            <div className="p-3 bg-white dark:bg-black rounded-md border border-slate-200 dark:border-slate-800">
                              <div className="flex items-center justify-between mb-2">
                                <h5 className="font-medium text-sm text-slate-800 dark:text-white flex items-center gap-2">
                                  <Shield className="h-4 w-4" />
                                  Uplift Check
                                </h5>
                                <div className="flex items-center gap-2">
                                  {result.uplift_check.is_safe ? (
                                    <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                                  ) : (
                                    <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" />
                                  )}
                                  <span className={`text-sm font-semibold ${
                                    result.uplift_check.is_safe ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                                  }`}>
                                    FOS: {result.uplift_check.fos.toFixed(3)}
                                  </span>
                                </div>
                              </div>
                              <div className="grid grid-cols-2 gap-3 text-xs">
                                <div>
                                  <div className="text-slate-500 dark:text-gray-400 mb-1">Uplift Force</div>
                                  <div className="font-medium text-slate-800 dark:text-white">
                                    {result.uplift_check.total_uplift_kn.toFixed(2)} kN
                                  </div>
                                  <div className="text-slate-500 dark:text-gray-400 mt-1">
                                    ({result.uplift_check.governing_case || "N/A"})
                                  </div>
                                </div>
                                <div>
                                  <div className="text-slate-500 dark:text-gray-400 mb-1">Resistance</div>
                                  <div className="font-medium text-slate-800 dark:text-white">
                                    {result.uplift_check.resistance_kn.toFixed(2)} kN
                                  </div>
                                  <div className={`text-xs mt-1 ${
                                    upliftMargin > 0.5 ? "text-green-600 dark:text-green-400" : upliftMargin > 0 ? "text-amber-600 dark:text-amber-400" : "text-red-600 dark:text-red-400"
                                  }`}>
                                    Safety Margin: {upliftMargin > 0 ? `+${(upliftMargin * 100).toFixed(1)}%` : `${(upliftMargin * 100).toFixed(1)}%`}
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Sliding Check */}
                            <div className="p-3 bg-white dark:bg-black rounded-md border border-slate-200 dark:border-slate-800">
                              <div className="flex items-center justify-between mb-2">
                                <h5 className="font-medium text-sm text-slate-800 dark:text-white flex items-center gap-2">
                                  <Shield className="h-4 w-4" />
                                  Sliding Check
                                </h5>
                                <div className="flex items-center gap-2">
                                  {result.sliding_check.is_safe ? (
                                    <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                                  ) : (
                                    <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" />
                                  )}
                                  <span className={`text-sm font-semibold ${
                                    result.sliding_check.is_safe ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                                  }`}>
                                    FOS: {result.sliding_check.fos.toFixed(3)}
                                  </span>
                                </div>
                              </div>
                              <div className="grid grid-cols-2 gap-3 text-xs">
                                <div>
                                  <div className="text-slate-500 dark:text-gray-400 mb-1">Lateral Force</div>
                                  <div className="font-medium text-slate-800 dark:text-white">
                                    {result.sliding_check.lateral_force_kn.toFixed(2)} kN
                                  </div>
                                </div>
                                <div>
                                  <div className="text-slate-500 dark:text-gray-400 mb-1">Resistance</div>
                                  <div className="font-medium text-slate-800 dark:text-white">
                                    {result.sliding_check.resistance_kn.toFixed(2)} kN
                                  </div>
                                  <div className={`text-xs mt-1 ${
                                    slidingMargin > 0.5 ? "text-green-600 dark:text-green-400" : slidingMargin > 0 ? "text-amber-600 dark:text-amber-400" : "text-red-600 dark:text-red-400"
                                  }`}>
                                    Safety Margin: {slidingMargin > 0 ? `+${(slidingMargin * 100).toFixed(1)}%` : `${(slidingMargin * 100).toFixed(1)}%`}
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Overturning Check */}
                            <div className="p-3 bg-white dark:bg-black rounded-md border border-slate-200 dark:border-slate-800">
                              <div className="flex items-center justify-between mb-2">
                                <h5 className="font-medium text-sm text-slate-800 dark:text-white flex items-center gap-2">
                                  <Shield className="h-4 w-4" />
                                  Overturning Check
                                </h5>
                                <div className="flex items-center gap-2">
                                  {result.overturning_check.is_safe ? (
                                    <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                                  ) : (
                                    <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" />
                                  )}
                                  <span className={`text-sm font-semibold ${
                                    result.overturning_check.is_safe ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                                  }`}>
                                    FOS: {result.overturning_check.fos.toFixed(3)}
                                  </span>
                                </div>
                              </div>
                              <div className="grid grid-cols-2 gap-3 text-xs">
                                <div>
                                  <div className="text-slate-500 dark:text-gray-400 mb-1">Overturning Moment</div>
                                  <div className="font-medium text-slate-800 dark:text-white">
                                    {result.overturning_check.overturning_moment_knm.toFixed(2)} kN·m
                                  </div>
                                </div>
                                <div>
                                  <div className="text-slate-500 dark:text-gray-400 mb-1">Resisting Moment</div>
                                  <div className="font-medium text-slate-800 dark:text-white">
                                    {result.overturning_check.resisting_moment_knm.toFixed(2)} kN·m
                                  </div>
                                  <div className={`text-xs mt-1 ${
                                    overturningMargin > 0.5 ? "text-green-600 dark:text-green-400" : overturningMargin > 0 ? "text-amber-600 dark:text-amber-400" : "text-red-600 dark:text-red-400"
                                  }`}>
                                    Safety Margin: {overturningMargin > 0 ? `+${(overturningMargin * 100).toFixed(1)}%` : `${(overturningMargin * 100).toFixed(1)}%`}
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Cost Comparison */}
                          {(wasAdjusted || result.status === "REQUIRES_PILING") && result.safety_cost_increase > 0 && (
                            <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md border border-blue-200 dark:border-blue-800">
                              <div className="flex items-center justify-between">
                                <div>
                                  <div className="text-sm text-slate-500 dark:text-gray-400">Original Cost</div>
                                  <div className="font-medium text-slate-800 dark:text-white">
                                    {formatCostDecimal(result.original_cost)}
                                  </div>
                                </div>
                                <div className="text-slate-400 dark:text-gray-500">→</div>
                                <div>
                                  <div className="text-sm text-slate-500 dark:text-gray-400">
                                    {result.status === "REQUIRES_PILING" ? "Piling Cost" : "Adjusted Cost"}
                                  </div>
                                  <div className="font-medium text-green-600 dark:text-green-400">
                                    {formatCostDecimal(result.original_cost + result.safety_cost_increase)}
                                  </div>
                                </div>
                                <div>
                                  <div className="text-sm text-slate-500 dark:text-gray-400">
                                    {result.status === "REQUIRES_PILING" ? "Piling Penalty" : "Safety Increase"}
                                  </div>
                                  <div className="font-semibold text-red-600 dark:text-red-400">
                                    +{formatCostDecimal(result.safety_cost_increase)}
                                  </div>
                                </div>
                              </div>
                              {result.reason && (
                                <div className="mt-2 text-xs text-muted-foreground">
                                  Reason: {result.reason}
                                </div>
                              )}
                            </div>
                          )}
                            </>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </CardContent>
              </Card>

              {/* Critical Alerts */}
              {validationResults.critical_alerts && validationResults.critical_alerts.length > 0 && (
                <Card className="bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-red-600 dark:text-red-400 text-lg flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5" />
                      Critical Alerts
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {validationResults.critical_alerts.map((alert: any, idx: number) => (
                        <div key={idx} className="p-3 rounded-md bg-white dark:bg-gray-800 border border-red-200 dark:border-red-800">
                          <div className="font-semibold text-red-600 dark:text-red-400">
                            Tower #{alert.tower_id + 1} (High Risk)
                          </div>
                          <ul className="list-disc list-inside text-sm text-muted-foreground mt-1">
                            {alert.issues.map((issue: string, i: number) => (
                              <li key={i}>{issue}</li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Cost Impact Analysis (Phase 2) */}
              {validationResults.total_safety_cost_increase > 0 && (
                <Card className="bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-blue-600 dark:text-blue-400 text-lg flex items-center gap-2">
                      <DollarSign className="h-5 w-5" />
                      Cost Impact Analysis
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <dl className="space-y-2">
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Optimized Bid Price</dt>
                        <dd className="font-medium">{formatCostDecimal(costBreakdown.foundation_total || 0)}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Safety-Certified Price</dt>
                        <dd className="font-medium text-green-600 dark:text-green-400">
                          {formatCostDecimal((costBreakdown.foundation_total || 0) + validationResults.total_safety_cost_increase)}
                        </dd>
                      </div>
                      <Separator />
                      <div className="flex justify-between">
                        <dt className="text-muted-foreground">Delta (Safety Surcharge)</dt>
                        <dd className="font-medium text-red-600 dark:text-red-400">
                          +{formatCostDecimal(validationResults.total_safety_cost_increase)}
                        </dd>
                      </div>
                    </dl>
                  </CardContent>
                </Card>
              )}

              {/* Download Safety Report Button */}
              <div className="flex justify-end">
                <Button
                  onClick={exportSafetyAuditToExcel}
                  variant="outline"
                  className="flex items-center gap-2"
                >
                  <Download className="h-4 w-4" />
                  Download Safety Report
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 7. Warnings */}
      {warnings.length > 0 && (
        <Card className="bg-card border-border border-amber-200 ">
          <CardHeader className="pb-3">
            <CardTitle className="text-slate-800 dark:text-white text-lg flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-amber-600 " />
              Constructability & Practicality Warnings
            </CardTitle>
            <CardDescription>Advisory warnings (not safety violations)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {warnings.map((warning: any, index: number) => (
              <div
                key={index}
                className="flex items-start gap-3 p-3 rounded-md bg-amber-50  border border-amber-200 "
              >
                <AlertTriangle className="h-5 w-5 text-amber-600  flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="text-sm font-medium text-amber-800  mb-1">
                    {warning.type === "cost_anomaly" ? "Cost Anomaly" : "Constructability Warning"}
                  </div>
                  <span className="text-sm text-amber-700 ">{warning.message || String(warning)}</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* 8. Advisories */}
      {advisories.length > 0 && (
        <Card className="bg-card border-border border-slate-200 dark:border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-slate-800 dark:text-white text-lg flex items-center gap-2">
              <Info className="h-5 w-5 text-slate-600 dark:text-gray-400" />
              Risk Advisories
            </CardTitle>
            <CardDescription>Region-specific design recommendations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {advisories.map((advisory: any, index: number) => (
              <div
                key={index}
                className="flex items-start gap-3 p-4 rounded-md bg-slate-50/50 dark:bg-black/20 border border-slate-200 dark:border-slate-800/50"
              >
                <Info className="h-5 w-5 text-slate-500 dark:text-gray-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="font-semibold text-slate-700 dark:text-gray-300 mb-2">
                    {advisory.risk_name || "Risk Advisory"}
                  </div>
                  <div className="text-sm text-slate-600 dark:text-gray-400 space-y-2">
                    <p><strong>Why it matters:</strong> {advisory.reason}</p>
                    <p><strong>Not currently evaluated:</strong> {advisory.not_evaluated}</p>
                    {advisory.suggested_action && (
                      <div className="mt-2 p-2 bg-slate-100/80 dark:bg-black/40 rounded border border-slate-200 dark:border-slate-800">
                        <p className="font-medium text-slate-700 dark:text-gray-300">{advisory.suggested_action}</p>
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
        <Card className="bg-card border-border border-slate-200 dark:border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-slate-800 dark:text-white text-lg flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-slate-600 dark:text-gray-400" />
              Constraint Log
            </CardTitle>
            <CardDescription>Automatic obstacle detection and tower adjustments</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Detected Obstacles */}
            {obstacles.length > 0 && (
              <div>
                <h4 className="font-semibold text-slate-800 dark:text-white mb-2">Detected Obstacles</h4>
                <ul className="space-y-2 text-sm">
                  {obstacles.map((obstacle: any, idx: number) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-slate-500 dark:text-gray-400">✅</span>
                      <span className="text-slate-700 dark:text-gray-300">
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
                <h4 className="font-semibold text-slate-800 dark:text-white mb-2">Tower Adjustments</h4>
                <ul className="space-y-2 text-sm">
                  {towers
                    .filter((t: any) => t.nudge_description)
                    .map((tower: any) => (
                      <li key={tower.index} className="flex items-start gap-2">
                        <span className="text-slate-500 dark:text-gray-400">🛠️</span>
                        <span className="text-slate-700 dark:text-gray-300">
                          Tower {tower.index + 1}: {tower.nudge_description}
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
            <div className="mt-4 p-3 bg-slate-50/50 dark:bg-black/20 rounded-md border border-slate-200 dark:border-slate-800">
              <p className="text-xs text-slate-600 dark:text-gray-400">
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
          <CardTitle className="text-slate-800 dark:text-white text-lg flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Market Rates Reference
          </CardTitle>
          <CardDescription>Regional construction cost rates used for calculations</CardDescription>
        </CardHeader>
        <CardContent>
          {costBreakdown?.market_rates ? (
            <div className="space-y-4">
              <div className="bg-slate-50 dark:bg-black/50 p-3 rounded-lg border border-slate-200 dark:border-slate-800">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-medium text-slate-800 dark:text-white">
                    {costBreakdown.market_rates?.market_note || costBreakdown.market_rates?.description || costBreakdown.market_note || "Market Rates"}
                  </p>
                  {(costBreakdown.market_rates?.market_source === "groq" || costBreakdown.market_source === "groq") && (
                    <Badge variant="outline" className="bg-blue-50 dark:bg-blue-900 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-700">
                      AI-Powered
                    </Badge>
                  )}
                </div>
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-muted-foreground">Steel Price</dt>
                    <dd className="font-medium text-slate-800 dark:text-white">
                      {costBreakdown.market_rates.currency_symbol || costBreakdown.currency_symbol || "$"}
                      {(costBreakdown.market_rates.steel_price_local_per_tonne || costBreakdown.market_rates.steel_price_usd)?.toLocaleString() || "N/A"} / tonne
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Concrete Price</dt>
                    <dd className="font-medium text-slate-800 dark:text-white">
                      {costBreakdown.market_rates.currency_symbol || costBreakdown.currency_symbol || "$"}
                      {(costBreakdown.market_rates.concrete_price_local_per_m3 || costBreakdown.market_rates.concrete_price_usd || costBreakdown.market_rates.cement_price_usd)?.toLocaleString() || "N/A"} / m³
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Labor Factor</dt>
                    <dd className="font-medium text-slate-800 dark:text-white">
                      {costBreakdown.market_rates.labor_factor?.toFixed(1) || "N/A"}x
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Logistics Factor</dt>
                    <dd className="font-medium text-slate-800 dark:text-white">
                      {costBreakdown.market_rates.logistics_factor?.toFixed(1) || "N/A"}x
                    </dd>
                  </div>
                </dl>
              </div>
              <p className="text-xs text-muted-foreground italic">
                {costBreakdown.market_rates.market_source === "groq" 
                  ? "Source: Real-time market rates via MarketOracle (AI-powered)"
                  : "Source: Global Construction Cost Reference Library (Q4 2024 / Q1 2025 Estimates)"}
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
            <CardTitle className="text-slate-800 dark:text-white text-lg">Optimization Metadata</CardTitle>
            <CardDescription>Optimization method and convergence information</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Optimization Method</dt>
                <dd className="font-medium text-slate-800 dark:text-white">PSO (Particle Swarm Optimization)</dd>
              </div>
              {optimizationInfo.iterations !== undefined && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Iterations Performed</dt>
                  <dd className="font-medium text-slate-800 dark:text-white">{optimizationInfo.iterations}</dd>
                </div>
              )}
              {optimizationInfo.converged !== undefined && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Convergence Status</dt>
                  <dd className="font-medium text-slate-800 dark:text-white">{optimizationInfo.converged ? "Converged" : "Not converged"}</dd>
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
            <CardTitle className="text-slate-800 dark:text-white text-lg flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              Cost Sensitivity Bands
            </CardTitle>
            <CardDescription>Expected cost range with variance</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Lower Bound</dt>
                <dd className="font-medium text-slate-800 dark:text-white">
                  {formatCostDecimal(results.cost_sensitivity?.lower_bound || 0)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Upper Bound</dt>
                <dd className="font-medium text-slate-800 dark:text-white">
                  {formatCostDecimal(results.cost_sensitivity?.upper_bound || 0)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Variance</dt>
                <dd className="font-medium text-slate-800 dark:text-white">
                  ±{results.cost_sensitivity?.variance_percent?.toFixed(1) || "0"}%
                </dd>
              </div>
              <Separator className="my-3" />
              <div className="flex justify-between pt-2">
                <dt className="font-semibold text-slate-800 dark:text-white">Expected Range</dt>
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
            <CardTitle className="text-slate-800 dark:text-white text-lg flex items-center gap-2">
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
            <CardTitle className="text-slate-800 dark:text-white text-lg">Confidence Score</CardTitle>
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

