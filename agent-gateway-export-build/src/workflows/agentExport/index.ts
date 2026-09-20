import type { AgentEventHistoryItem, AgentSubstrateExport } from '@/lib/agent-substrate/schema'
import {
  loadConnections,
  loadEventHistoryPage,
  loadKnowledge,
  loadSelectedAgent,
  recordExportAuditEvent,
  redactSensitiveConnectionFields,
  validateExportPayload,
} from './steps'

export async function exportAgentSubstrateWorkflow(agentId: string): Promise<AgentSubstrateExport> {
  'use workflow'

  const agent = await loadSelectedAgent(agentId)
  const knowledge = await loadKnowledge(agentId)
  const rawConnections = await loadConnections(agentId)
  const connections = await redactSensitiveConnectionFields(rawConnections)

  const eventHistory: AgentEventHistoryItem[] = []
  let cursor: string | undefined = undefined
  let partial = false

  try {
    for (let pageCount = 0; pageCount < 100; pageCount += 1) {
      const page = await loadEventHistoryPage(agentId, cursor)
      eventHistory.push(...page.items)
      if (!page.nextCursor) break
      cursor = page.nextCursor
    }
  } catch {
    partial = true
  }

  const exportedAt = new Date().toISOString()

  const payload = await validateExportPayload({
    schemaVersion: 'agent-substrate-export.v1',
    agentId: agent.id,
    name: agent.name,
    version: agent.version,
    exportedAt,
    partial,
    knowledge,
    connections,
    eventHistory,
  })

  await recordExportAuditEvent(payload)

  return payload
}
