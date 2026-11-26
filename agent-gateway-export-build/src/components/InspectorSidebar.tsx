'use client'

import { useState } from 'react'

type SelectedAgent = {
  id: string
  name: string
  description?: string
}

type InspectorSidebarProps = {
  selectedAgent?: SelectedAgent | null
}

function filenameFromContentDisposition(header: string | null, fallback: string) {
  if (!header) return fallback
  const match = header.match(/filename="?([^";]+)"?/i)
  return match?.[1] || fallback
}

export function InspectorSidebar({ selectedAgent }: InspectorSidebarProps) {
  const [isDownloading, setIsDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function downloadAgentExport() {
    if (!selectedAgent || isDownloading) return

    setIsDownloading(true)
    setError(null)

    try {
      const response = await fetch(`/api/agents/${encodeURIComponent(selectedAgent.id)}/export`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
      })

      if (!response.ok) {
        const payload = await response.json().catch(() => null)
        throw new Error(payload?.error?.message || 'Export failed. Please try again.')
      }

      const blob = await response.blob()
      const filename = filenameFromContentDisposition(
        response.headers.get('Content-Disposition'),
        `agent-${selectedAgent.id}-export.json`,
      )

      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = filename
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : 'Export failed. Please try again.')
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <aside className="inspector-sidebar" aria-label="Agent inspector">
      <div className="inspector-header">
        <p className="eyebrow">Inspector</p>
        <h2>{selectedAgent ? selectedAgent.name : 'No agent selected'}</h2>
        {selectedAgent?.description ? <p className="muted">{selectedAgent.description}</p> : null}
      </div>

      <div className="inspector-body">
        <button
          type="button"
          onClick={downloadAgentExport}
          disabled={!selectedAgent || isDownloading}
          className="primary-button"
          aria-busy={isDownloading}
        >
          {isDownloading ? 'Preparing export…' : 'Download'}
        </button>

        <p className="helper-text">
          Exports the selected agent’s knowledge, safe connection metadata, and event history as JSON.
        </p>

        {error ? (
          <div role="alert" className="error-box">
            {error}
          </div>
        ) : null}
      </div>
    </aside>
  )
}
