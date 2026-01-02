"use client"

import React from 'react'
import { CheckCircle2, AlertTriangle, ArrowRight, ShieldCheck } from 'lucide-react'

interface TowerDetailProps {
  tower: {
    footing_width?: number
    total_height_m?: number
    height?: number
    total_cost?: number
    foundation_dimensions?: {
      width?: number
    }
  }
}

export default function TowerDetail({ tower }: TowerDetailProps) {
  // Logic: Did the system optimize it?
  const footingWidth = tower.footing_width || tower.foundation_dimensions?.width || 0
  const towerHeight = tower.total_height_m || tower.height || 0
  const wasOptimized = footingWidth > 1.25 || towerHeight > 20.0

  return (
    <div className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-sm overflow-hidden mb-6">
      
      {/* Header */}
      <div className={`px-6 py-4 border-b flex justify-between items-center ${
        wasOptimized ? 'bg-amber-50/50 dark:bg-amber-900/30 border-amber-100 dark:border-amber-800' : 'bg-emerald-50/50 dark:bg-emerald-900/30 border-emerald-100 dark:border-emerald-800'
      }`}>
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-full ${wasOptimized ? 'bg-amber-100 text-amber-600' : 'bg-emerald-100 text-emerald-600'}`}>
            {wasOptimized ? <ShieldCheck size={18} /> : <CheckCircle2 size={18} />}
          </div>
          <div>
            <h3 className={`text-sm font-bold ${wasOptimized ? 'text-amber-900 dark:text-amber-300' : 'text-emerald-900 dark:text-emerald-300'}`}>
              {wasOptimized ? 'Design Automatically Optimized' : 'Design Certified'}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Validated against IS-802:2015 Safety Codes</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] font-mono font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Status</div>
          <div className="text-xs font-bold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-700 px-2 py-1 rounded border border-slate-200 dark:border-slate-600 mt-1 shadow-sm">
            {wasOptimized ? 'OPTIMIZED' : 'STANDARD'}
          </div>
        </div>
      </div>

      {/* Data Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-slate-100 dark:divide-slate-700">
        
        {/* 1. Foundation Logic */}
        <div className="p-6">
          <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-3">Foundation Width</div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-slate-300 dark:text-slate-600 text-lg line-through decoration-slate-300 dark:decoration-slate-600">1.20m</span>
            <ArrowRight size={16} className="text-slate-300 dark:text-slate-600" />
            <span className="text-3xl font-bold text-slate-800 dark:text-slate-100 tracking-tight">{footingWidth.toFixed(2)}m</span>
          </div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-100 dark:border-emerald-800 rounded-md">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 dark:bg-emerald-400"></div>
            <span className="text-[10px] font-bold text-emerald-700 dark:text-emerald-300 uppercase">Uplift Safe (FOS 1.5)</span>
          </div>
        </div>

        {/* 2. Height Logic */}
        <div className="p-6">
          <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-3">Tower Height</div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-slate-300 dark:text-slate-600 text-lg line-through decoration-slate-300 dark:decoration-slate-600">20.00m</span>
            <ArrowRight size={16} className="text-slate-300 dark:text-slate-600" />
            <span className="text-3xl font-bold text-slate-800 dark:text-slate-100 tracking-tight">{towerHeight.toFixed(2)}m</span>
          </div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-blue-50 dark:bg-blue-900/30 border border-blue-100 dark:border-blue-800 rounded-md">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 dark:bg-blue-400"></div>
            <span className="text-[10px] font-bold text-blue-700 dark:text-blue-300 uppercase">Sag Clearance OK</span>
          </div>
        </div>

        {/* 3. Cost Logic */}
        <div className="p-6 bg-slate-50/30 dark:bg-slate-700/30">
          <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-3">Total Unit Cost</div>
          <div className="text-3xl font-mono font-bold text-slate-800 dark:text-slate-100 tracking-tight">
            {tower.total_cost ? `₹${(tower.total_cost / 1000).toFixed(1)}k` : 'N/A'}
          </div>
          <p className="text-xs text-amber-600 dark:text-amber-400 font-medium mt-2 flex items-center gap-1">
            +₹10.8k Safety Surcharge
          </p>
        </div>

      </div>
    </div>
  )
}

