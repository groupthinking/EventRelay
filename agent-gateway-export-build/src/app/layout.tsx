import './globals.css'
import type { ReactNode } from 'react'

export const metadata = {
  title: 'Agent Substrate Export',
  description: 'AI Gateway and selected-agent JSON export flow.',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
