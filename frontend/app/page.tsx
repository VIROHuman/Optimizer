"use client"

import * as React from "react"
import LandingPage from "@/components/landing-page"
import AppLayout from "@/components/app-layout"
import TowerOptimizerForm from "@/components/tower-optimizer-form"
import OptimizationResults from "@/components/optimization-results"
import { normalizePayload, runOptimization } from "@/lib/api"

type View = "landing" | "app"
type AppSection = "dashboard" | "new" | "saved" | "reference" | "about"

export default function Home() {
  const [view, setView] = React.useState<View>("landing")
  const [activeSection, setActiveSection] = React.useState<AppSection>("new")
  const [showResults, setShowResults] = React.useState(false)
  const [isLoading, setIsLoading] = React.useState(false)
  const [results, setResults] = React.useState<any>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [projectLength, setProjectLength] = React.useState<number>(50) // Frontend-only: Project length in km

  const handleStartOptimization = () => {
    setView("app")
    setActiveSection("new")
  }

  const handleNavigate = (id: string) => {
    // Map new layout menu items to existing sections
    const sectionMap: Record<string, AppSection> = {
      'dashboard': 'dashboard',
      'route': 'new',
      'towers': 'new',
      'cost': 'new',
      'reports': 'new',
    }
    const mappedSection = sectionMap[id] || 'new'
    setActiveSection(mappedSection)
    setShowResults(false)
    setResults(null)
    setError(null)
  }

  const handleRunOptimization = async (data: any) => {
    setIsLoading(true)
    setError(null)
    setShowResults(false)
    
    try {
      // Store project length for display
      const projectLengthNum = Number(data.projectLength) || 50
      setProjectLength(projectLengthNum)
      
      // Normalize payload to match backend schema exactly
      // projectLength is now sent to backend for canonical format
      const payload = normalizePayload(data)
      
      // Log payload for debugging
      console.log("Sending payload:", payload)
      
      // Call backend API
      const result = await runOptimization(payload)
      
      setResults(result)
      setShowResults(true)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to run optimization"
      setError(errorMessage)
      setShowResults(false)
      console.error("Optimization error:", err)
    } finally {
      setIsLoading(false)
    }
  }

  if (view === "landing") {
    return <LandingPage onStartOptimization={handleStartOptimization} />
  }

  const handleBackToLanding = () => {
    setView("landing")
    setShowResults(false)
    setResults(null)
    setError(null)
  }

  return (
    <AppLayout
      projectName="400kV Narnaul Line"
      activeItem={activeSection}
      onNavigate={handleNavigate}
      onBackToLanding={handleBackToLanding}
    >
      {activeSection === "new" && (
        <div className="space-y-6">
          <TowerOptimizerForm onSubmit={handleRunOptimization} isLoading={isLoading} />
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md shadow-sm">
              <p className="text-red-800">Error: {error}</p>
            </div>
          )}
          {showResults && results && <OptimizationResults results={results} projectLength={projectLength} />}
        </div>
      )}
      {activeSection === "dashboard" && (
        <div className="text-center py-12 text-muted-foreground">Dashboard view - Coming soon</div>
      )}
      {activeSection === "saved" && (
        <div className="text-center py-12 text-muted-foreground">Saved Runs - Coming soon</div>
      )}
      {activeSection === "reference" && (
        <div className="text-center py-12 text-muted-foreground">Reference Data - Coming soon</div>
      )}
      {activeSection === "about" && <div className="text-center py-12 text-muted-foreground">About - Coming soon</div>}
    </AppLayout>
  )
}
