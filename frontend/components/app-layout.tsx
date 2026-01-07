"use client"

import React, { useState, useEffect } from 'react'
import { LayoutDashboard, Map, HardHat, BarChart3, FileText, ChevronRight, LogOut, Moon, Sun, Home, ChevronLeft } from 'lucide-react'

interface AppLayoutProps {
  children: React.ReactNode
  projectName?: string
  activeItem?: string
  onNavigate?: (id: string) => void
  onBackToLanding?: () => void
}

const menuItems = [
  { id: 'dashboard', label: 'Project Dashboard', icon: <LayoutDashboard size={18} /> },
  { id: 'route', label: 'Route Definition', icon: <Map size={18} /> },
  { id: 'towers', label: 'Tower Schedule', icon: <HardHat size={18} /> },
  { id: 'cost', label: 'Cost Analysis', icon: <BarChart3 size={18} /> },
  { id: 'reports', label: 'Reports & Exports', icon: <FileText size={18} /> },
]

export default function AppLayout({
  children,
  projectName = "Alpha: 400kV Narnaul Line",
  activeItem = "dashboard",
  onNavigate,
  onBackToLanding,
}: AppLayoutProps) {
  const [activeTab, setActiveTab] = useState(activeItem || 'dashboard')
  const [isDark, setIsDark] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  useEffect(() => {
    // Check for saved theme preference or default to light
    const savedTheme = localStorage.getItem('theme')
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    const shouldBeDark = savedTheme === 'dark' || (!savedTheme && prefersDark)
    setIsDark(shouldBeDark)
    if (shouldBeDark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [])

  const toggleTheme = () => {
    const newTheme = !isDark
    setIsDark(newTheme)
    if (newTheme) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }

  const handleTabClick = (id: string) => {
    setActiveTab(id)
    onNavigate?.(id)
  }

  return (
    <div className="flex min-h-screen bg-[#F8FAFC] dark:bg-black font-sans text-slate-900 dark:text-white">
      
      {/* --- FIXED SIDEBAR --- */}
      <aside className={`${sidebarCollapsed ? 'w-16' : 'w-64'} bg-white dark:bg-black border-r border-slate-200 dark:border-slate-800 flex flex-col fixed h-full z-40 shadow-[2px_0_8px_-3px_rgba(0,0,0,0.05)] transition-all duration-300`}>
        
        {/* Brand */}
        <div className="h-16 flex items-center px-6 border-b border-slate-100 dark:border-slate-800">
          <div className="w-8 h-8 bg-[#005EB8] dark:bg-blue-600 rounded flex items-center justify-center mr-3 font-bold text-white flex-shrink-0">L</div>
          {!sidebarCollapsed && (
            <div>
              <h1 className="font-bold text-slate-800 dark:text-white text-sm tracking-tight">GRID<span className="text-[#005EB8] dark:text-blue-400">OPT</span> SUITE</h1>
              <p className="text-[10px] text-slate-400 dark:text-gray-500 font-semibold uppercase tracking-wider">Enterprise v2.0</p>
            </div>
          )}
        </div>

        {/* Menu */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {!sidebarCollapsed && (
            <div className="px-2 mb-2 text-[10px] font-bold text-slate-400 dark:text-gray-500 uppercase tracking-widest">Main Modules</div>
          )}
          {menuItems.map((item) => (
            <button
              key={item.id}
              onClick={() => handleTabClick(item.id)}
              className={`w-full flex items-center ${sidebarCollapsed ? 'justify-center' : 'gap-3'} px-3 py-2.5 rounded-md text-sm font-medium transition-all duration-200 group ${
                activeTab === item.id 
                  ? 'bg-blue-50 dark:bg-black text-[#005EB8] dark:text-blue-400 border border-blue-100 dark:border-slate-800' 
                  : 'text-slate-500 dark:text-gray-400 hover:bg-slate-50 dark:hover:bg-gray-900 hover:text-slate-900 dark:hover:text-white'
              }`}
              title={sidebarCollapsed ? item.label : undefined}
            >
              <span className={activeTab === item.id ? 'text-[#005EB8] dark:text-blue-400' : 'text-slate-400 dark:text-gray-500 group-hover:text-slate-600 dark:group-hover:text-gray-300'}>{item.icon}</span>
              {!sidebarCollapsed && <span>{item.label}</span>}
              {!sidebarCollapsed && activeTab === item.id && <ChevronRight size={14} className="ml-auto opacity-50" />}
            </button>
          ))}
        </nav>

        {/* User Badge & Controls */}
        <div className="p-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-black">
          {!sidebarCollapsed ? (
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-white dark:bg-gray-900 border border-slate-200 dark:border-slate-800 flex items-center justify-center text-[#005EB8] dark:text-blue-400 font-bold text-xs shadow-sm">AK</div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-bold text-slate-700 dark:text-white truncate">Aravind K.</p>
                  <p className="text-[10px] text-slate-400 dark:text-gray-500 truncate">L&T Energy - PT&D</p>
                </div>
              </div>
              <div className="flex items-center gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                <button
                  onClick={toggleTheme}
                  className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-gray-900 transition-colors"
                  aria-label="Toggle theme"
                  title="Toggle theme"
                >
                  {isDark ? <Sun size={14} className="text-slate-400 dark:text-gray-400" /> : <Moon size={14} className="text-slate-400" />}
                </button>
                {onBackToLanding && (
                  <button
                    onClick={onBackToLanding}
                    className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-gray-900 transition-colors"
                    aria-label="Back to landing"
                    title="Back to landing"
                  >
                    <Home size={14} className="text-slate-400 dark:text-gray-400" />
                  </button>
                )}
                <button
                  onClick={() => setSidebarCollapsed(true)}
                  className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-gray-900 transition-colors ml-auto"
                  aria-label="Collapse sidebar"
                  title="Collapse sidebar"
                >
                  <ChevronLeft size={14} className="text-slate-400 dark:text-gray-400" />
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <button
                onClick={() => setSidebarCollapsed(false)}
                className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-gray-900 transition-colors"
                aria-label="Expand sidebar"
                title="Expand sidebar"
              >
                <ChevronRight size={14} className="text-slate-400 dark:text-gray-400" />
              </button>
              <button
                onClick={toggleTheme}
                className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-gray-900 transition-colors"
                aria-label="Toggle theme"
                title="Toggle theme"
              >
                {isDark ? <Sun size={14} className="text-slate-400 dark:text-gray-400" /> : <Moon size={14} className="text-slate-400" />}
              </button>
              {onBackToLanding && (
                <button
                  onClick={onBackToLanding}
                  className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-gray-900 transition-colors"
                  aria-label="Back to landing"
                  title="Back to landing"
                >
                  <Home size={14} className="text-slate-400 dark:text-gray-400" />
                </button>
              )}
            </div>
          )}
        </div>
      </aside>

      {/* --- MAIN CONTENT AREA --- */}
      <main className={`flex-1 ${sidebarCollapsed ? 'ml-16' : 'ml-64'} flex flex-col min-w-0 transition-all duration-300`}>
        
        {/* Header Bar */}
        <header className="h-16 bg-white dark:bg-black border-b border-slate-200 dark:border-slate-800 px-8 flex items-center justify-between sticky top-0 z-30 shadow-sm">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 dark:text-gray-500 text-sm">Projects /</span>
            <span className="font-semibold text-slate-800 dark:text-white text-sm">{projectName}</span>
            <span className="ml-2 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 uppercase tracking-wide">
              Draft Estimate
            </span>
          </div>
        </header>

        {/* Content Injector */}
        <div className="p-8 space-y-6 bg-[#F8FAFC] dark:bg-black">
          {children}
        </div>
      </main>
    </div>
  )
}
