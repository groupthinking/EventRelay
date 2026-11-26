import {
  getAgentById,
  getAgentConnections,
  getAgentEventHistoryPage,
  getAgentKnowledge,
  recordAgentExportAuditEvent,
} from '@/lib/agent-substrate/store'
import {
  redactConnection,
  validateAgentExport,
  type AgentConnectionExport,
  type AgentEventHistoryItem,
  type AgentSubstrateExport,
} from '@/lib/agent-substrate/schema'

export async function loadSelectedAgent(agentId: string) {
  'use step'
  return getAgentById(agentId)
}

export async function loadKnowledge(agentId: string) {
  'use step'
  return getAgentKnowledge(agentId)
}

export async function loadConnections(agentId: string) {
  'use step'
  return getAgentConnections(agentId)
}

export async function loadEventHistoryPage(agentId: string, cursor?: string) {
  'use step'
  return getAgentEventHistoryPage(agentId, cursor)
}

export async function redactSensitiveConnectionFields(connections: AgentConnectionExport[]) {
  'use step'
  return connections.map(redactConnection)
}

export async function validateExportPayload(payload: AgentSubstrateExport) {
  'use step'
  return validateAgentExport(payload)
}

export async function recordExportAuditEvent(payload: AgentSubstrateExport) {
  'use step'
  await recordAgentExportAuditEvent(payload.agentId, {
    exportedAt: payload.exportedAt,
    itemCounts: {
      knowledge: payload.knowledge.length,
      connections: payload.connections.length,
      eventHistory: payload.eventHistory.length,
    },
  })
  return { ok: true }
}

export type EventHistoryAccumulator = {
  items: AgentEventHistoryItem[]
  partial: boolean
}
