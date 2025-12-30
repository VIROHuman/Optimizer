import type { Metadata } from "next"
import type { ReactNode } from "react"
import { Geist, Geist_Mono } from "next/font/google"
import { Analytics } from "@vercel/analytics/next"
import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "sonner"
import "./globals.css"

const geist = Geist({ subsets: ["latin"], variable: "--font-geist" })
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" })

export const metadata: Metadata = {
  title: "Transmission Line Design Optimizer | Larsen & Toubro",
  description: "L&T Power - Codal-compliant, physics-based optimization for HV transmission towers",
  generator: "Larsen & Toubro",
  icons: {
    icon: [
      { url: "/L&T.png", media: "(prefers-color-scheme: light)" },
      { url: "/lnt.png", media: "(prefers-color-scheme: dark)" },
    ],
    apple: "/L&T.png",
  },
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geist.variable} ${geistMono.variable} font-sans antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
        <Toaster position="top-right" />
        <Analytics />
      </body>
    </html>
  )
}
