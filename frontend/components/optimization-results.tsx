"use client"

import { Separator } from "@/components/ui/separator"
import { CheckCircle, AlertTriangle, Info, FileText, DollarSign, Building2, Shield, AlertCircle } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface OptimizationResultsProps {
  results: any
  projectLength?: number // Frontend-only: Project length in km (default 50)
}

export default function OptimizationResults({ results, projectLength = 50 }: OptimizationResultsProps) {
  if (!results) return null

  const design = results.design || {}
  const cost = results.cost || {}
  const safety = results.safety || {}
  const warnings = results.warnings || []
  const advisories = results.advisories || []
  const projectContext = results.project_context || {}
  const lineLevelSummary = results.line_level_summary || {}
  const regionalRisks = results.regional_risks || []
  const referenceDataStatus = results.reference_data_status || {}
  const designScenariosApplied = results.design_scenarios_applied || []
  const optimizationInfo = results.optimization_info || {}
  const codalEngineName = results.codal_engine_name || "N/A"

  // Frontend-only calculations for line-level project planning
  const spanLength = lineLevelSummary.span_length || design.span_length || 0
  const costPerKm = lineLevelSummary.total_cost_per_km || 0
  const currencySymbol = lineLevelSummary.currency_symbol || cost.currency_symbol || "$"
  const currency = lineLevelSummary.currency || cost.currency || "USD"
  
  // Calculate derived metrics
  const towerDensity = spanLength > 0 ? 1000 / spanLength : 0
  const estimatedTowers = Math.round(towerDensity * projectLength)
  const totalProjectCost = costPerKm * projectLength
  
  // Format cost for display (handle Indian Rupees with "Cr" for crores)
  const formatProjectCost = (cost: number, symbol: string, curr: string) => {
    if (curr === "INR" && cost >= 10000000) {
      // For INR, use Crores (Cr) for values >= 1 Cr
      return `${symbol}${(cost / 10000000).toFixed(1)} Cr`
    }
    return `${symbol}${cost.toLocaleString()}`
  }

  return (
    <div className="space-y-6">
      {/* Header with Safety Status */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-foreground">Optimization Results</h2>
        <Badge
          variant={safety.is_safe ? "default" : "destructive"}
          className={safety.is_safe ? "bg-green-600 hover:bg-green-700" : ""}
        >
          {safety.is_safe ? (
            <CheckCircle className="h-3.5 w-3.5 mr-1" />
          ) : (
            <AlertTriangle className="h-3.5 w-3.5 mr-1" />
          )}
          {safety.is_safe ? "SAFE" : "UNSAFE"}
        </Badge>
      </div>

      {/* 1. Project & Codal Context */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-foreground text-lg flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Project & Codal Context
          </CardTitle>
          <CardDescription>Project location and governing design standards</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm text-muted-foreground">Project Location</dt>
              <dd className="font-medium text-foreground">{projectContext.location || "N/A"}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Governing Standard</dt>
              <dd className="font-medium text-foreground">{projectContext.governing_standard || "N/A"}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Codal Engine</dt>
              <dd className="font-medium text-foreground">{codalEngineName}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Voltage Level</dt>
              <dd className="font-medium text-foreground">{projectContext.voltage_level || "N/A"} kV</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Wind Zone</dt>
              <dd className="font-medium text-foreground">{projectContext.wind_zone || "N/A"}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted-foreground">Soil Category</dt>
              <dd className="font-medium text-foreground">{projectContext.soil || "N/A"}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {/* Results Grid */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* 2. Best Design Geometry */}
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg">Best Design Geometry</CardTitle>
            <CardDescription>Optimized tower structural parameters</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Tower Type</dt>
                <dd className="font-medium text-foreground">{design.tower_type || "N/A"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Tower Height</dt>
                <dd className="font-medium text-foreground">{design.tower_height?.toFixed(2) || "N/A"} m</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Base Width</dt>
                <dd className="font-medium text-foreground">{design.base_width?.toFixed(2) || "N/A"} m</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Span Length</dt>
                <dd className="font-medium text-foreground">{design.span_length?.toFixed(2) || "N/A"} m</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        {/* 3. Foundation Details */}
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg">Foundation Details</CardTitle>
            <CardDescription>Recommended foundation specifications</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Foundation Type</dt>
                <dd className="font-medium text-foreground">{design.foundation_type || "N/A"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Footing Length</dt>
                <dd className="font-medium text-foreground">{design.footing_length?.toFixed(2) || "N/A"} m</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Footing Width</dt>
                <dd className="font-medium text-foreground">{design.footing_width?.toFixed(2) || "N/A"} m</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Footing Depth</dt>
                <dd className="font-medium text-foreground">{design.footing_depth?.toFixed(2) || "N/A"} m</dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      </div>

      {/* 4. Cost Breakdown - Per Tower */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-foreground text-lg flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Cost Breakdown — Per Tower
          </CardTitle>
          <CardDescription>Estimated costs per single tower</CardDescription>
        </CardHeader>
        <CardContent>
          {cost.total_cost ? (
            <>
              <dl className="space-y-3">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Steel Structure Cost</dt>
                  <dd className="font-medium text-foreground">
                    {cost.currency_symbol || "$"}{cost.steel_cost?.toLocaleString() || "0"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Foundation Cost</dt>
                  <dd className="font-medium text-foreground">
                    {cost.currency_symbol || "$"}{cost.foundation_cost?.toLocaleString() || "0"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Transport & Erection Cost</dt>
                  <dd className="font-medium text-foreground">
                    {cost.currency_symbol || "$"}{cost.erection_cost?.toLocaleString() || "0"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Land / ROW Cost</dt>
                  <dd className="font-medium text-foreground">
                    {cost.currency_symbol || "$"}{cost.land_cost?.toLocaleString() || "0"}
                  </dd>
                </div>
                <div className="border-t border-border my-3" />
                <div className="flex justify-between pt-2">
                  <dt className="font-semibold text-foreground">Total Cost per Tower</dt>
                  <dd className="font-bold text-blue-600 dark:text-blue-400">
                    {cost.currency_symbol || "$"}{cost.total_cost?.toLocaleString() || "0"} {cost.currency || "USD"}
                  </dd>
                </div>
              </dl>

              {/* 6. Regional Multipliers */}
              {cost.regional_multipliers && (
                <div className="mt-6 pt-6 border-t border-border">
                  <h4 className="text-sm font-semibold text-foreground mb-3">
                    Regional Multipliers ({cost.regional_multipliers.region?.toUpperCase() || "N/A"})
                  </h4>
                  <dl className="grid grid-cols-2 gap-3 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-muted-foreground">Steel</dt>
                      <dd className="font-medium text-foreground">×{cost.regional_multipliers.steel?.toFixed(2) || "1.00"}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-muted-foreground">Materials</dt>
                      <dd className="font-medium text-foreground">×{cost.regional_multipliers.materials?.toFixed(2) || "1.00"}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-muted-foreground">Labor</dt>
                      <dd className="font-medium text-foreground">×{cost.regional_multipliers.labor?.toFixed(2) || "1.00"}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-muted-foreground">Access</dt>
                      <dd className="font-medium text-foreground">×{cost.regional_multipliers.access?.toFixed(2) || "1.00"}</dd>
                    </div>
                  </dl>
                </div>
              )}
            </>
          ) : (
            <p className="text-muted-foreground">Cost data not available for unsafe designs</p>
          )}
        </CardContent>
      </Card>

      {/* 5. Line-Level Economic Summary */}
      {lineLevelSummary.total_cost_per_km && (
        <Card className="bg-card border-border border-blue-200 dark:border-blue-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg flex items-center gap-2">
              <Building2 className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              Line-Level Economic Summary
            </CardTitle>
            <CardDescription>Cost per kilometer of transmission line (optimization objective)</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Span Length</dt>
                <dd className="font-medium text-foreground">{lineLevelSummary.span_length?.toFixed(2) || "N/A"} m</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Towers per km</dt>
                <dd className="font-medium text-foreground">{lineLevelSummary.towers_per_km?.toFixed(3) || "N/A"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Cost per tower</dt>
                <dd className="font-medium text-foreground">
                  {lineLevelSummary.currency_symbol || "$"}{lineLevelSummary.cost_per_tower?.toLocaleString() || "0"}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">ROW Corridor Cost per km</dt>
                <dd className="font-medium text-foreground">
                  {lineLevelSummary.currency_symbol || "$"}{lineLevelSummary.row_corridor_cost_per_km?.toLocaleString() || "0"} /km
                </dd>
              </div>
              <Separator className="my-3" />
              <div className="flex justify-between pt-2">
                <dt className="font-semibold text-foreground">TOTAL Estimated Cost per km</dt>
                <dd className="font-bold text-blue-600 dark:text-blue-400">
                  {lineLevelSummary.currency_symbol || "$"}{lineLevelSummary.total_cost_per_km?.toLocaleString() || "0"}{" "}
                  {lineLevelSummary.currency || "USD"}/km
                </dd>
              </div>
            </dl>
            <p className="text-xs text-muted-foreground mt-4 italic">
              Note: Line-level cost per kilometer is the primary optimization objective.
            </p>
          </CardContent>
        </Card>
      )}

      {/* 5b. Line-Level Project Summary */}
      {lineLevelSummary.total_cost_per_km && spanLength > 0 && (
        <Card className="bg-card border-border border-green-200 dark:border-green-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg flex items-center gap-2">
              <Building2 className="h-5 w-5 text-green-600 dark:text-green-400" />
              Line-Level Project Summary
            </CardTitle>
            <CardDescription>Planning metrics scaled to project length (frontend calculation)</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Span Length</dt>
                <dd className="font-medium text-foreground">{spanLength.toFixed(2)} m</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">
                  Tower Density
                  <span className="ml-2 text-xs" title="Tower density is an average planning metric. Actual tower count will be an integer.">
                    ℹ️
                  </span>
                </dt>
                <dd className="font-medium text-foreground">{towerDensity.toFixed(2)} towers / km</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Project Length</dt>
                <dd className="font-medium text-foreground">{projectLength} km</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Estimated Towers</dt>
                <dd className="font-medium text-foreground">~{estimatedTowers}</dd>
              </div>
              <Separator className="my-3" />
              <div className="flex justify-between pt-2">
                <dt className="font-semibold text-foreground">Estimated Line Cost</dt>
                <dd className="font-bold text-green-600 dark:text-green-400">
                  {formatProjectCost(totalProjectCost, currencySymbol, currency)}
                </dd>
              </div>
            </dl>
            <p className="text-xs text-muted-foreground mt-4 italic">
              Note: These are planning estimates based on optimized per-km metrics. Actual tower count will be an integer based on terrain and survey.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Safety Status */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-foreground text-lg flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Safety Status
          </CardTitle>
          <CardDescription>Structural safety assessment</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Overall Status</dt>
              <dd
                className={`font-semibold ${safety.is_safe ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}
              >
                {safety.is_safe ? "SAFE" : "UNSAFE"}
              </dd>
            </div>
            {!safety.is_safe && safety.violations && safety.violations.length > 0 && (
              <div className="pt-2">
                <dt className="text-muted-foreground mb-2">Violations:</dt>
                <ul className="list-disc list-inside space-y-1">
                  {safety.violations.map((violation: string, idx: number) => (
                    <li key={idx} className="text-sm text-red-600 dark:text-red-400">{violation}</li>
                  ))}
                </ul>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>

      {/* 7. Constructability & Practicality Warnings */}
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

      {/* 8. Regional Risk Context */}
      {regionalRisks.length > 0 && (
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg">Regional Risk Context</CardTitle>
            <CardDescription>Informational risks for this region</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {regionalRisks.map((risk: any, index: number) => (
                <li key={index} className="flex items-start gap-2 text-sm">
                  <Info className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                  <span className="text-foreground">{typeof risk === "string" ? risk : risk.name || risk.message || JSON.stringify(risk)}</span>
                </li>
              ))}
            </ul>
            <p className="text-xs text-muted-foreground mt-4 italic">
              Note: These risks are informational and not automatically included in design unless selected.
            </p>
          </CardContent>
        </Card>
      )}

      {/* 9. Dominant Regional Risk Advisories */}
      {advisories.length > 0 && (
        <Card className="bg-card border-border border-blue-200 dark:border-blue-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-foreground text-lg flex items-center gap-2">
              <Info className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              Dominant Regional Risk Advisories
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

      {/* 10. Design Scenarios Applied */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-foreground text-lg">Design Scenarios Applied</CardTitle>
          <CardDescription>Additional design scenarios enabled for this optimization</CardDescription>
        </CardHeader>
        <CardContent>
          {designScenariosApplied.length > 0 ? (
            <ul className="space-y-2">
              {designScenariosApplied.map((scenario: string, index: number) => (
                <li key={index} className="flex items-start gap-2 text-sm">
                  <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
                  <span className="text-foreground">{scenario}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted-foreground text-sm">No additional design scenarios applied.</p>
          )}
        </CardContent>
      </Card>

      {/* 11. Reference Data Status */}
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

      {/* 12. Optimization Metadata */}
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
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Iterations Performed</dt>
              <dd className="font-medium text-foreground">{optimizationInfo.iterations || "N/A"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Convergence Status</dt>
              <dd className="font-medium text-foreground">{optimizationInfo.converged ? "Converged" : "Not converged"}</dd>
            </div>
          </dl>
          <Separator className="my-4" />
          <p className="text-xs text-muted-foreground italic">
            This is a DECISION-SUPPORT TOOL. Final designs must be reviewed by qualified engineers before implementation.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
