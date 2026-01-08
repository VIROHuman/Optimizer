"use client"

import React, { useState, useEffect } from 'react'
import { LayoutDashboard, Map, HardHat, BarChart3, FileText, ChevronRight, LogOut, Moon, Sun, Home, ChevronLeft, Edit2, X } from 'lucide-react'

interface UserProfile {
  initials?: string
  name?: string
  department?: string
}

interface AppLayoutProps {
  children?: React.ReactNode
  projectName?: string
  activeItem?: string
  onNavigate?: (id: string) => void
  onBackToLanding?: () => void
  renderContent?: (activeTab: string) => React.ReactNode
  userProfile?: UserProfile
  onUserProfileUpdate?: (profile: UserProfile) => void
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
  projectName = "TowerOpt",
  activeItem = "dashboard",
  onNavigate,
  onBackToLanding,
  renderContent,
  userProfile = { initials: 'AK', name: 'Aravind K.', department: 'L&T Energy - PT&D' },
  onUserProfileUpdate,
}: AppLayoutProps) {
  const [activeTab, setActiveTab] = useState(activeItem || 'dashboard')
  const [isDark, setIsDark] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [showProfileEdit, setShowProfileEdit] = useState(false)
  const [editedProfile, setEditedProfile] = useState<UserProfile>(userProfile)

  // Sync activeTab with activeItem prop changes
  useEffect(() => {
    if (activeItem) {
      setActiveTab(activeItem)
    }
  }, [activeItem])

  // Sync editedProfile when userProfile prop changes
  useEffect(() => {
    setEditedProfile(userProfile)
  }, [userProfile])

  const handleSaveProfile = () => {
    onUserProfileUpdate?.(editedProfile)
    setShowProfileEdit(false)
  }

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

  // Determine what content to render
  const contentToRender = renderContent ? renderContent(activeTab) : children

  return (
    <div className="flex min-h-screen bg-[#F8FAFC] dark:bg-black font-sans text-slate-900 dark:text-white">
      
      {/* --- FIXED SIDEBAR --- */}
      <aside className={`${sidebarCollapsed ? 'w-16' : 'w-64'} bg-white dark:bg-black border-r border-neutral-800 flex flex-col fixed h-full z-40 shadow-[2px_0_8px_-3px_rgba(0,0,0,0.05)] transition-all duration-300`}>
        
        {/* Brand */}
        <div className="h-16 flex items-center px-6 border-b border-neutral-800">
          <div className="w-8 h-8 bg-[#005EB8] dark:bg-blue-600 rounded flex items-center justify-center mr-3 font-bold text-white flex-shrink-0">L</div>
          {!sidebarCollapsed && (
            <div>
              <h1 className="font-bold text-slate-800 dark:text-white text-sm tracking-tight">GRID<span className="text-[#005EB8] dark:text-blue-400">OPT</span> SUITE</h1>
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
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-[#005EB8] dark:text-blue-400 border border-neutral-800' 
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
        <div className="p-4 border-t border-neutral-800 bg-slate-50/50 dark:bg-black">
          {!sidebarCollapsed ? (
            <div className="space-y-2">
              <div className="flex items-center gap-3 p-2 rounded-md bg-white dark:bg-black border border-neutral-800">
                <div className="w-8 h-8 rounded-full bg-white dark:bg-gray-900 border border-neutral-800 flex items-center justify-center text-[#005EB8] dark:text-blue-400 font-bold text-xs shadow-sm">
                  {userProfile.initials || 'AK'}
                </div>
                <div className="flex-1 min-w-0">
                  {userProfile.name && (
                    <p className="text-xs font-bold text-slate-700 dark:text-white truncate">{userProfile.name}</p>
                  )}
                  {userProfile.department && (
                    <p className="text-[10px] text-slate-400 dark:text-gray-500 truncate">{userProfile.department}</p>
                  )}
                </div>
                <button
                  onClick={() => setShowProfileEdit(true)}
                  className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-gray-900 transition-colors flex-shrink-0"
                  aria-label="Edit profile"
                  title="Edit profile"
                >
                  <Edit2 size={12} className="text-slate-400 dark:text-gray-400" />
                </button>
              </div>
              <div className="flex items-center gap-2 pt-2 border-t border-neutral-800">
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
        <header className="h-16 bg-white dark:bg-black border-b border-neutral-800 px-8 flex items-center justify-between sticky top-0 z-30 shadow-sm">
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
          {contentToRender}
        </div>
      </main>

      {/* User Profile Edit Modal */}
      {showProfileEdit && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={() => setShowProfileEdit(false)}
        >
          <div 
            className="bg-white dark:bg-black border border-neutral-800 rounded-lg shadow-xl w-full max-w-md mx-4 p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-slate-800 dark:text-white">Edit Profile</h2>
              <button
                onClick={() => setShowProfileEdit(false)}
                className="p-1 rounded-md hover:bg-slate-100 dark:hover:bg-gray-900 transition-colors"
                aria-label="Close"
              >
                <X size={18} className="text-slate-400 dark:text-gray-400" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700 dark:text-gray-300">
                  Initials
                </label>
                <input
                  type="text"
                  value={editedProfile.initials || ''}
                  onChange={(e) => setEditedProfile({ ...editedProfile, initials: e.target.value })}
                  className="w-full px-3 py-2 rounded-md border border-neutral-800 bg-white dark:bg-black text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="e.g., AK"
                  maxLength={4}
                />
              </div>
              
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700 dark:text-gray-300">
                  Name
                </label>
                <input
                  type="text"
                  value={editedProfile.name || ''}
                  onChange={(e) => setEditedProfile({ ...editedProfile, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-md border border-neutral-800 bg-white dark:bg-black text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="e.g., Aravind K."
                />
              </div>
              
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700 dark:text-gray-300">
                  Department
                </label>
                <input
                  type="text"
                  value={editedProfile.department || ''}
                  onChange={(e) => setEditedProfile({ ...editedProfile, department: e.target.value })}
                  className="w-full px-3 py-2 rounded-md border border-neutral-800 bg-white dark:bg-black text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="e.g., L&T Energy - PT&D"
                />
              </div>
            </div>
            
            <div className="flex items-center justify-end gap-2 mt-6 pt-4 border-t border-neutral-800">
              <button
                onClick={() => {
                  setEditedProfile(userProfile)
                  setShowProfileEdit(false)
                }}
                className="px-4 py-2 rounded-md text-sm font-medium text-slate-700 dark:text-gray-300 hover:bg-slate-100 dark:hover:bg-gray-900 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveProfile}
                className="px-4 py-2 rounded-md text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition-colors"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
