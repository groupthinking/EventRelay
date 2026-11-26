export type FailureCode =
  | 'auth'
  | 'not_found'
  | 'schema_invalid'
  | 'gateway_unavailable'
  | 'event_history_partial'
  | 'download_client_error'

export class ExportFailure extends Error {
  code: FailureCode
  status: number
  details?: unknown

  constructor(code: FailureCode, message: string, status = 500, details?: unknown) {
    super(message)
    this.name = 'ExportFailure'
    this.code = code
    this.status = status
    this.details = details
  }
}

export type AgentKnowledgeItem = {
  id: string
  title: string
  content: string
  source?: string
  updatedAt?: string
}

export type AgentConnectionExport = {
  id: string
  name: string
  type: string
  status: 'ready' | 'disabled' | 'error' | 'unknown'
  scopes?: string[]
  metadata?: Record<string, unknown>
}

export type AgentEventHistoryItem = {
  id: string
  type: string
  timestamp: string
  summary: string
  metadata?: Record<string, unknown>
}

export type AgentSubstrateExport = {
  schemaVersion: 'agent-substrate-export.v1'
  agentId: string
  name: string
  version: string
  exportedAt: string
  partial: boolean
  knowledge: AgentKnowledgeItem[]
  connections: AgentConnectionExport[]
  eventHistory: AgentEventHistoryItem[]
  checksum?: string
}

const SECRET_KEY_PATTERN = /(api[_-]?key|token|secret|password|authorization|credential|private[_-]?key|refresh[_-]?token|access[_-]?token|client[_-]?secret|env)/i

export function redactValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(redactValue)
  if (!value || typeof value !== 'object') return value

  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).map(([key, nested]) => {
      if (SECRET_KEY_PATTERN.test(key)) return [key, '[REDACTED]']
      return [key, redactValue(nested)]
    }),
  )
}

export function redactConnection(connection: AgentConnectionExport): AgentConnectionExport {
  return {
    ...connection,
    metadata: connection.metadata ? (redactValue(connection.metadata) as Record<string, unknown>) : undefined,
  }
}

export function validateAgentExport(payload: AgentSubstrateExport): AgentSubstrateExport {
  if (payload.schemaVersion !== 'agent-substrate-export.v1') {
    throw new ExportFailure('schema_invalid', 'Invalid export schema version.', 500)
  }
  if (!payload.agentId || !payload.name || !payload.exportedAt) {
    throw new ExportFailure('schema_invalid', 'Export is missing required agent identity fields.', 500)
  }
  if (!Array.isArray(payload.knowledge) || !Array.isArray(payload.connections) || !Array.isArray(payload.eventHistory)) {
    throw new ExportFailure('schema_invalid', 'Export sections must be arrays.', 500)
  }
  return payload
}

export function safeExportFilename(agentName: string, exportedAt = new Date().toISOString()): string {
  const slug = agentName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 64) || 'agent'
  const date = exportedAt.slice(0, 10)
  return `agent-${slug}-export-${date}.json`
}
