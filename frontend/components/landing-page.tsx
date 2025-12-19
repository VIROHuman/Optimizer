"use client"

import { Zap, Shield, DollarSign, AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Logo } from "@/components/logo"
import { ThemeToggle } from "@/components/theme-toggle"

const features = [
  {
    icon: Zap,
    title: "Physics-based Optimization",
    description: "Advanced structural analysis using real-world physics models for accurate tower design calculations.",
  },
  {
    icon: Shield,
    title: "International Code Compliance",
    description: "Full compliance with IS, IEC, EN, and ASCE standards for global deployment readiness.",
  },
  {
    icon: DollarSign,
    title: "Cost & Constructability Awareness",
    description: "Optimize designs for both performance and economic efficiency with constructability insights.",
  },
]

interface LandingPageProps {
  onStartOptimization?: () => void
}

export default function LandingPage({ onStartOptimization }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <Logo width={40} height={40} />
              <span className="font-semibold text-foreground text-lg">L&T Power</span>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-4xl sm:text-5xl font-bold text-foreground mb-6 text-balance">
            Transmission Line Design Optimizer
          </h1>
          <p className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto text-pretty">
            Codal-compliant, physics-based optimization for HV transmission towers
          </p>
          <Button
            size="lg"
            className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 text-lg"
            onClick={onStartOptimization}
          >
            Start Optimization
          </Button>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 bg-muted/50">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl font-semibold text-foreground text-center mb-12">Key Capabilities</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {features.map((feature) => (
              <Card key={feature.title} className="bg-card border-border">
                <CardHeader>
                  <div className="w-12 h-12 rounded-lg bg-blue-600/10 dark:bg-blue-400/10 flex items-center justify-center mb-4">
                    <feature.icon className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                  </div>
                  <CardTitle className="text-foreground">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-muted-foreground text-base">{feature.description}</CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Disclaimer Section */}
      <section className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          <Card className="border-amber-500/50 bg-amber-50/50 dark:bg-amber-950/20">
            <CardContent className="flex items-start gap-4 pt-6">
              <AlertTriangle className="h-6 w-6 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-amber-800 dark:text-amber-300 mb-2">Engineering Disclaimer</h3>
                <p className="text-amber-700 dark:text-amber-400/80 text-sm">
                  This is a decision-support tool. Final designs must be reviewed by qualified engineers before
                  implementation. All outputs should be validated against applicable codes and standards.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto flex items-center justify-center gap-3">
          <Logo width={24} height={24} />
          <span className="text-sm text-muted-foreground">
            © {new Date().getFullYear()} L&T Power. All rights reserved.
          </span>
        </div>
      </footer>
    </div>
  )
}
