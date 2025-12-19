"use client"

import * as React from "react"
import { LayoutDashboard, Plus, Save, Database, Info, ChevronLeft, User } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Logo } from "@/components/logo"
import { ThemeToggle } from "@/components/theme-toggle"

const sidebarItems = [
  { icon: LayoutDashboard, label: "Dashboard", id: "dashboard" },
  { icon: Plus, label: "New Optimization", id: "new" },
  { icon: Save, label: "Saved Runs", id: "saved" },
  { icon: Database, label: "Reference Data", id: "reference" },
  { icon: Info, label: "About", id: "about" },
]

interface AppLayoutProps {
  children: React.ReactNode
  projectName?: string
  activeItem?: string
  onNavigate?: (id: string) => void
}

export default function AppLayout({
  children,
  projectName = "Untitled Project",
  activeItem = "dashboard",
  onNavigate,
}: AppLayoutProps) {
  const [collapsed, setCollapsed] = React.useState(false)

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 h-full bg-card border-r border-border flex flex-col transition-all duration-200 z-40",
          collapsed ? "w-16" : "w-64",
        )}
      >
        {/* Sidebar Header */}
        <div className="h-16 border-b border-border flex items-center px-4 gap-3">
          <Logo width={32} height={32} />
          {!collapsed && <span className="font-semibold text-foreground truncate">L&T Power</span>}
        </div>

        {/* Sidebar Navigation */}
        <nav className="flex-1 py-4 px-2">
          {sidebarItems.map((item) => (
            <button
              key={item.id}
              onClick={() => onNavigate?.(item.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors mb-1",
                activeItem === item.id
                  ? "bg-blue-600/10 text-blue-600 dark:bg-blue-400/10 dark:text-blue-400"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </button>
          ))}
        </nav>

        {/* Collapse Button */}
        <div className="p-2 border-t border-border">
          <Button variant="ghost" size="sm" className="w-full justify-center" onClick={() => setCollapsed(!collapsed)}>
            <ChevronLeft className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")} />
          </Button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className={cn("flex-1 flex flex-col transition-all duration-200", collapsed ? "ml-16" : "ml-64")}>
        {/* Top Header */}
        <header className="h-16 border-b border-border bg-card flex items-center justify-between px-6 sticky top-0 z-30">
          <h1 className="font-semibold text-foreground truncate">{projectName}</h1>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <div className="flex items-center gap-2 pl-3 border-l border-border">
              <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                <User className="h-4 w-4 text-muted-foreground" />
              </div>
              <span className="text-sm text-muted-foreground hidden sm:inline">User</span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>
    </div>
  )
}
