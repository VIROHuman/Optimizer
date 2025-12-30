"use client"

import * as React from "react"
import { useTheme } from "next-themes"
import Image from "next/image"

interface LogoProps {
  className?: string
  width?: number
  height?: number
}

export function Logo({ className = "", width = 48, height = 48 }: LogoProps) {
  const { resolvedTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return <div className={`bg-slate-200 dark:bg-slate-700 rounded ${className}`} style={{ width, height }} />
  }

  return (
    <Image
      src={resolvedTheme === "dark" ? "/lnt.png" : "/L&T.png"}
      alt="L&T Logo"
      width={width}
      height={height}
      className={`${className} object-contain`}
      priority
    />
  )
}
