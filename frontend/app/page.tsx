"use client"

import * as React from "react"
import LandingPage from "@/components/landing-page"
import AppLayout from "@/components/app-layout"
import TowerOptimizerForm from "@/components/tower-optimizer-form"
import OptimizationResults from "@/components/optimization-results"
import { normalizePayload, runOptimization } from "@/lib/api"

type View = "landing" | "app"
type AppSection = "dashboard" | "route" | "towers" | "cost" | "reports"

interface UserProfile {
  initials?: string
  name?: string
  department?: string
}

export default function Home() {
  const [view, setView] = React.useState<View>("landing")
  const [activeSection, setActiveSection] = React.useState<AppSection>("route")
  const [showResults, setShowResults] = React.useState(false)
  const [isLoading, setIsLoading] = React.useState(false)
  const [results, setResults] = React.useState<any>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [projectLength, setProjectLength] = React.useState<number>(50) // Frontend-only: Project length in km
  const [userProfile, setUserProfile] = React.useState<UserProfile>(() => {
    // Load from localStorage if available
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('userProfile')
      if (saved) {
        try {
          return JSON.parse(saved)
        } catch {
          // Fallback to default if parse fails
        }
      }
    }
    return { initials: 'AK', name: 'Aravind K.', department: 'L&T Energy - PT&D' }
  })

  const handleStartOptimization = () => {
    setView("app")
    setActiveSection("route")
  }

  const handleNavigate = (id: string) => {
    // Update active section to match the sidebar menu item
    setActiveSection(id as AppSection)
    // Clear results when switching tabs (except when staying on route)
    if (id !== 'route') {
      setShowResults(false)
      setResults(null)
      setError(null)
    }
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

  const handleUserProfileUpdate = (profile: UserProfile) => {
    setUserProfile(profile)
    // Save to localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem('userProfile', JSON.stringify(profile))
    }
  }

  const renderContent = (activeTab: string) => {
    // Map sidebar menu items to content sections
    if (activeTab === 'route') {
      return (
        <div className="space-y-6">
          <TowerOptimizerForm onSubmit={handleRunOptimization} isLoading={isLoading} />
          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md shadow-sm">
              <p className="text-red-800 dark:text-red-300">Error: {error}</p>
            </div>
          )}
          {showResults && results && <OptimizationResults results={results} projectLength={projectLength} />}
        </div>
      )
    }
    
    if (activeTab === 'dashboard') {
      return (
        <div className="text-center py-12 text-slate-500 dark:text-gray-400">
          Dashboard view - Coming soon
        </div>
      )
    }
    
    if (activeTab === 'towers') {
      return (
        <div className="text-center py-12 text-slate-500 dark:text-gray-400">
          Tower Schedule view - Coming soon
        </div>
      )
    }
    
    if (activeTab === 'cost') {
      return (
        <div className="text-center py-12 text-slate-500 dark:text-gray-400">
          Cost Analysis view - Coming soon
        </div>
      )
    }
    
    if (activeTab === 'reports') {
      return (
        <div className="text-center py-12 text-slate-500 dark:text-gray-400">
          Reports & Exports view - Coming soon
        </div>
      )
    }
    
    // Default fallback
    return (
      <div className="text-center py-12 text-slate-500 dark:text-gray-400">
        Select a module from the sidebar
      </div>
    )
  }

  return (
    <AppLayout
      projectName="400kV Narnaul Line"
      activeItem={activeSection}
      onNavigate={handleNavigate}
      onBackToLanding={handleBackToLanding}
      renderContent={renderContent}
      userProfile={userProfile}
      onUserProfileUpdate={handleUserProfileUpdate}
    />
  )
}
