"use client"

import { Separator } from "@/components/ui/separator"
import { CheckCircle, AlertTriangle, Info, FileText, DollarSign, Building2, Shield, AlertCircle, MapPin, Route } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useState } from "react"

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
  const warnings = results.warnings || []
  const advisories = results.advisories || []
  const referenceDataStatus = results.reference_data_status || {}
  const optimizationInfo = results.optimization_info || {}

  // Format cost for display (handle Indian Rupees with "Cr" for crores)
  const formatCost = (cost: number, symbol: string, curr: string) => {
    if (curr === "INR" && cost >= 10000000) {
      return `${symbol}${(cost / 10000000).toFixed(1)} Cr`
    }
    return `${symbol}${cost.toLocaleString()}`
  }

  // Format cost with decimals
  const formatCostDecimal = (cost: number, symbol: string) => {
    return `${symbol}${cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
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
                  {formatCost(costContext.cost_per_km || 0, costBreakdown?.currency_symbol || "$", costBreakdown?.currency || "USD")}
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
                  </tr>
                </thead>
                <tbody>
                  {towers.map((tower: any, idx: number) => (
                    <tr key={idx} className="border-b border-border">
                      <td className="p-2 font-medium">{tower.index}</td>
                      <td className="p-2">{tower.tower_type}</td>
                      <td className="p-2">{tower.total_height_m?.toFixed(2)}</td>
                      <td className="p-2">{tower.foundation_dimensions?.width?.toFixed(2) || "N/A"}</td>
                      <td className="p-2">{tower.steel_weight_kg?.toLocaleString()}</td>
                      <td className="p-2">
                        {formatCostDecimal(
                          tower.total_cost || 0,
                          costBreakdown.currency_symbol || "$"
                        )}
                      </td>
                      <td className="p-2">
                        <Badge
                          variant={tower.safety_status === "SAFE" ? "default" : "secondary"}
                          className={tower.safety_status === "SAFE" ? "bg-green-600" : ""}
                        >
                          {tower.safety_status}
                        </Badge>
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
                  {formatCostDecimal(
                    lineSummary.cost_per_km || 0,
                    costBreakdown.currency_symbol || "$"
                  )}
                </dd>
              </div>
              {lineSummary.total_project_cost && (
                <div className="flex justify-between pt-2">
                  <dt className="font-semibold text-foreground">Total Project Cost</dt>
                  <dd className="font-bold text-blue-600 dark:text-blue-400">
                    {formatCost(
                      lineSummary.total_project_cost || 0,
                      costBreakdown.currency_symbol || "$",
                      costBreakdown.currency || "USD"
                    )}
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
                  {formatCostDecimal(costBreakdown.steel_total || 0, costBreakdown.currency_symbol || "$")}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Foundation Total</dt>
                <dd className="font-medium text-foreground">
                  {formatCostDecimal(costBreakdown.foundation_total || 0, costBreakdown.currency_symbol || "$")}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Erection Total</dt>
                <dd className="font-medium text-foreground">
                  {formatCostDecimal(costBreakdown.erection_total || 0, costBreakdown.currency_symbol || "$")}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Transport Total</dt>
                <dd className="font-medium text-foreground">
                  {formatCostDecimal(costBreakdown.transport_total || 0, costBreakdown.currency_symbol || "$")}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Land/ROW Total</dt>
                <dd className="font-medium text-foreground">
                  {formatCostDecimal(costBreakdown.land_ROW_total || 0, costBreakdown.currency_symbol || "$")}
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
                  {formatCostDecimal(
                    results.cost_sensitivity?.lower_bound || 0,
                    costBreakdown.currency_symbol || "$"
                  )}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Upper Bound</dt>
                <dd className="font-medium text-foreground">
                  {formatCostDecimal(
                    results.cost_sensitivity?.upper_bound || 0,
                    costBreakdown.currency_symbol || "$"
                  )}
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

