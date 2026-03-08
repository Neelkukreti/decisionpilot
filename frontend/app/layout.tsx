import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'DecisionPilot — Autonomous Meeting Execution',
  description: 'Extract decisions from meetings, validate quality, auto-create Jira tickets via Amazon Nova',
  icons: {
    icon: '/icon.svg',
    shortcut: '/icon.svg',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className + ' bg-[#0F1117] min-h-screen'}>
        {children}
      </body>
    </html>
  )
}
