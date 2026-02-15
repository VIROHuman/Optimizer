"use client"

import React, { useEffect, useState } from 'react'
import { ArrowLeft, Eye, EyeOff, Lock, Mail, Moon, Sun, Shield } from 'lucide-react'

interface LoginPageProps {
    onBackToLanding?: () => void
    onLoginSuccess?: () => void
}

export default function LoginPage({ onBackToLanding, onLoginSuccess }: LoginPageProps) {
    const [isDark, setIsDark] = useState(false)
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

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

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError(null)

        if (!email.trim() || !password.trim()) {
            setError('Please enter both email and password.')
            return
        }

        setIsLoading(true)

        // Simulated authentication delay
        await new Promise((resolve) => setTimeout(resolve, 1200))

        // For now, accept any credentials and proceed
        setIsLoading(false)
        onLoginSuccess?.()
    }

    return (
        <div className="min-h-screen bg-[#F8FAFC] dark:bg-slate-900 flex flex-col font-sans text-slate-900 dark:text-slate-100">

            {/* Corporate Header */}
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
                <div className="flex items-center gap-3">
                    <button
                        onClick={toggleTheme}
                        className="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                        aria-label="Toggle theme"
                    >
                        {isDark ? <Sun size={18} className="text-slate-600 dark:text-slate-300" /> : <Moon size={18} className="text-slate-600" />}
                    </button>
                    {onBackToLanding && (
                        <button
                            onClick={onBackToLanding}
                            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-all duration-200"
                        >
                            <ArrowLeft size={16} />
                            Back to Home
                        </button>
                    )}
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 flex items-center justify-center p-6">
                <div className="w-full max-w-md">

                    {/* Login Card */}
                    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-xl shadow-slate-200/50 dark:shadow-black/20 overflow-hidden">

                        {/* Card Header — Blue accent strip */}
                        <div className="h-1.5 bg-gradient-to-r from-[#005EB8] via-blue-500 to-[#005EB8]" />

                        <div className="p-8">
                            {/* Icon + Title */}
                            <div className="text-center mb-8">
                                <div className="w-14 h-14 bg-blue-50 dark:bg-blue-900/30 rounded-xl flex items-center justify-center mx-auto mb-4 border border-blue-100 dark:border-blue-800">
                                    <Shield className="text-[#005EB8] dark:text-blue-400" size={28} />
                                </div>
                                <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
                                    Welcome Back
                                </h2>
                                <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
                                    Sign in to access the Optimization Suite
                                </p>
                            </div>

                            {/* Error Message */}
                            {error && (
                                <div className="mb-6 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300">
                                    {error}
                                </div>
                            )}

                            {/* Login Form */}
                            <form onSubmit={handleSubmit} className="space-y-5">
                                {/* Email Field */}
                                <div className="space-y-2">
                                    <label htmlFor="email" className="block text-sm font-semibold text-slate-700 dark:text-slate-300">
                                        Email Address
                                    </label>
                                    <div className="relative">
                                        <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500 pointer-events-none" />
                                        <input
                                            id="email"
                                            type="email"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            placeholder="engineer@larsentoubro.com"
                                            className="w-full pl-10 pr-4 py-3 rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-[#005EB8]/40 focus:border-[#005EB8] dark:focus:ring-blue-500/40 dark:focus:border-blue-500 transition-all duration-200 text-sm"
                                            autoComplete="email"
                                        />
                                    </div>
                                </div>

                                {/* Password Field */}
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <label htmlFor="password" className="block text-sm font-semibold text-slate-700 dark:text-slate-300">
                                            Password
                                        </label>
                                        <button
                                            type="button"
                                            className="text-xs font-medium text-[#005EB8] dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
                                        >
                                            Forgot password?
                                        </button>
                                    </div>
                                    <div className="relative">
                                        <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500 pointer-events-none" />
                                        <input
                                            id="password"
                                            type={showPassword ? 'text' : 'password'}
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            placeholder="Enter your password"
                                            className="w-full pl-10 pr-12 py-3 rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-[#005EB8]/40 focus:border-[#005EB8] dark:focus:ring-blue-500/40 dark:focus:border-blue-500 transition-all duration-200 text-sm"
                                            autoComplete="current-password"
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowPassword(!showPassword)}
                                            className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                                            aria-label={showPassword ? 'Hide password' : 'Show password'}
                                        >
                                            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                                        </button>
                                    </div>
                                </div>

                                {/* Remember me */}
                                <div className="flex items-center gap-2">
                                    <input
                                        id="remember"
                                        type="checkbox"
                                        className="w-4 h-4 rounded border-slate-300 dark:border-slate-600 text-[#005EB8] focus:ring-[#005EB8] dark:focus:ring-blue-500 bg-white dark:bg-slate-900"
                                    />
                                    <label htmlFor="remember" className="text-sm text-slate-600 dark:text-slate-400 select-none">
                                        Remember me for 30 days
                                    </label>
                                </div>

                                {/* Submit Button */}
                                <button
                                    type="submit"
                                    disabled={isLoading}
                                    className="w-full py-3.5 bg-[#005EB8] dark:bg-blue-600 text-white font-semibold rounded-lg shadow-lg shadow-blue-500/20 hover:bg-blue-700 dark:hover:bg-blue-700 hover:shadow-xl hover:shadow-blue-500/30 disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-200 transform hover:-translate-y-0.5 disabled:transform-none text-sm tracking-wide"
                                >
                                    {isLoading ? (
                                        <span className="inline-flex items-center gap-2">
                                            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                            </svg>
                                            Signing in…
                                        </span>
                                    ) : (
                                        'Sign In'
                                    )}
                                </button>
                            </form>

                            {/* Divider */}
                            <div className="relative my-7">
                                <div className="absolute inset-0 flex items-center">
                                    <div className="w-full border-t border-slate-200 dark:border-slate-700" />
                                </div>
                                <div className="relative flex justify-center text-xs">
                                    <span className="bg-white dark:bg-slate-800 px-3 text-slate-400 dark:text-slate-500 font-medium uppercase tracking-wider">
                                        Secure access
                                    </span>
                                </div>
                            </div>

                            {/* Security note */}
                            <p className="text-center text-xs text-slate-400 dark:text-slate-500 leading-relaxed">
                                This portal is restricted to authorized L&T personnel.<br />
                                All sessions are encrypted and monitored.
                            </p>
                        </div>
                    </div>

                    {/* Footer text below card */}
                    <p className="text-center text-xs text-slate-400 dark:text-slate-500 mt-6">
                        &copy; 2026 Larsen & Toubro Limited. All rights reserved.
                    </p>
                </div>
            </main>
        </div>
    )
}
