"use client"

import React, { useEffect, useState } from 'react'
import { ArrowRight, Activity, ShieldCheck, Ruler, Moon, Sun, LogIn } from 'lucide-react'

interface LandingPageProps {
  onStartOptimization?: () => void
  onLogin?: () => void
}

const FeatureCard = ({ icon, title, desc }: { icon: React.ReactNode, title: string, desc: string }) => (
  <div className="p-6 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-shadow">
    <div className="w-10 h-10 bg-slate-50 dark:bg-slate-700 rounded-lg flex items-center justify-center mb-4 border border-slate-100 dark:border-slate-600">
      {icon}
    </div>
    <h3 className="font-bold text-slate-900 dark:text-slate-100 mb-2">{title}</h3>
    <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{desc}</p>
  </div>
)

export default function LandingPage({ onStartOptimization, onLogin }: LandingPageProps) {
  const [isDark, setIsDark] = useState(false)

  useEffect(() => {
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

  return (
    <div className="min-h-screen bg-[#F8FAFC] dark:bg-slate-900 flex flex-col font-sans text-slate-900 dark:text-slate-100">

      {/* 1. Corporate Header */}
      <header className="h-20 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-8 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-[#005EB8] rounded flex items-center justify-center text-white font-bold text-xl shadow-sm">
            L
          </div>
          <div>
            <h1 className="font-bold text-lg leading-none tracking-tight">Larsen & Toubro</h1>
            <p className="text-xs text-slate-500 font-medium tracking-wide mt-1">PT&D • DIGITAL SOLUTIONS</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            aria-label="Toggle theme"
          >
            {isDark ? <Sun size={18} className="text-slate-600 dark:text-slate-300" /> : <Moon size={18} className="text-slate-600" />}
          </button>
          <button
            onClick={onLogin}
            className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-[#005EB8] dark:text-blue-400 border border-[#005EB8]/30 dark:border-blue-500/30 rounded-lg hover:bg-[#005EB8] hover:text-white dark:hover:bg-blue-600 dark:hover:text-white transition-all duration-200 shadow-sm hover:shadow-md"
          >
            <LogIn size={16} />
            Login
          </button>
        </div>
      </header>

      {/* 2. Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-4xl mx-auto mt-10">
        <div className="mb-6 inline-flex items-center px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-900/30 border border-blue-100 dark:border-blue-800 text-[#005EB8] dark:text-blue-400 text-xs font-bold uppercase tracking-wider">
          Internal Engineering Tool v2.4
        </div>

        <h1 className="text-5xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight mb-6">
          Transmission Line <br />
          <span className="text-[#005EB8] dark:text-blue-400">Optimization Suite</span>
        </h1>

        <p className="text-lg text-slate-600 dark:text-slate-300 max-w-2xl mb-10 leading-relaxed">
          Automated route optimization, structural validation, and cost estimation for HV transmission towers.
          Compliant with <span className="font-semibold text-slate-800 dark:text-slate-200">IS-802</span> and <span className="font-semibold text-slate-800 dark:text-slate-200">IEC-60826</span>.
        </p>

        <button
          onClick={onStartOptimization}
          className="group relative inline-flex items-center justify-center px-8 py-4 bg-[#005EB8] dark:bg-blue-600 text-white text-lg font-semibold rounded-lg shadow-lg hover:bg-blue-700 dark:hover:bg-blue-700 hover:shadow-xl transition-all duration-200 transform hover:-translate-y-0.5"
        >
          Initialize New Project
          <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </button>

        {/* 3. Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-20 w-full text-left">
          <FeatureCard
            icon={<Activity className="text-blue-600" />}
            title="Physics-Based Solver"
            desc="Real-time conductor sag & tension analysis with wind gradient modeling."
          />
          <FeatureCard
            icon={<ShieldCheck className="text-emerald-600" />}
            title="Safety Validation"
            desc="Automatic foundation sizing to meet Uplift & Overturning FOS > 1.5."
          />
          <FeatureCard
            icon={<Ruler className="text-amber-600" />}
            title="Cost Estimation"
            desc="Class-4 feasibility estimates with localized material & labor rates."
          />
        </div>
      </main>

      {/* Footer */}
      <footer className="py-8 text-center text-slate-400 dark:text-slate-500 text-xs mt-auto border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
        &copy; 2026 Larsen & Toubro Limited. All rights reserved. | <span className="font-mono">CONFIDENTIAL - INTERNAL USE ONLY</span>
      </footer>
    </div>
  )
}
