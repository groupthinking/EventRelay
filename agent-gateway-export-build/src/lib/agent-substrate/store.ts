import type { AgentConnectionExport, AgentEventHistoryItem, AgentKnowledgeItem } from './schema'
import { ExportFailure } from './schema'

type AgentRecord = {
  id: string
  name: string
  version: string
}

const demoAgents: AgentRecord[] = [
  { id: 'agent-demo', name: 'Demo Agent', version: '0.1.0' },
]

const demoKnowledge: AgentKnowledgeItem[] = [
  {
    id: 'k-001',
    title: 'AI Gateway Deployment Path',
    content: 'Use the ai SDK with Vercel OIDC. Pull env locally with vc env pull .env.local.',
    source: 'architect-plan',
    updatedAt: new Date('2026-07-31T00:00:00.000Z').toISOString(),
  },
]

const demoConnections: AgentConnectionExport[] = [
  {
    id: 'conn-vercel',
    name: 'Vercel AI Gateway',
    type: 'ai-gateway',
    status: 'ready',
    scopes: ['model:invoke'],
    metadata: {
      project: 'replace-with-project-id',
      accessToken: 'must-not-export',
      nested: { apiKey: 'must-not-export' },
    },
  },
]

const demoEvents: AgentEventHistoryItem[] = [
  {
    id: 'evt-001',
    type: 'agent.selected',
    timestamp: new Date('2026-07-31T00:01:00.000Z').toISOString(),
    summary: 'Agent selected in inspector.',
  },
  {
    id: 'evt-002',
    type: 'export.requested',
    timestamp: new Date('2026-07-31T00:02:00.000Z').toISOString(),
    summary: 'User requested JSON export.',
  },
]

export async function getAgentById(agentId: string): Promise<AgentRecord> {
  const agent = demoAgents.find((candidate) => candidate.id === agentId)
  if (!agent) throw new ExportFailure('not_found', 'Selected agent was not found.', 404)
  return agent
}

export async function getAgentKnowledge(agentId: string): Promise<AgentKnowledgeItem[]> {
  await getAgentById(agentId)
  return demoKnowledge
}

export async function getAgentConnections(agentId: string): Promise<AgentConnectionExport[]> {
  await getAgentById(agentId)
  return demoConnections
}

export async function getAgentEventHistoryPage(
  agentId: string,
  cursor?: string,
): Promise<{ items: AgentEventHistoryItem[]; nextCursor?: string }> {
  await getAgentById(agentId)
  if (cursor && cursor !== 'page-2') return { items: [], nextCursor: undefined }
  if (!cursor) return { items: demoEvents.slice(0, 1), nextCursor: 'page-2' }
  return { items: demoEvents.slice(1), nextCursor: undefined }
}

export async function recordAgentExportAuditEvent(
  agentId: string,
  payload: { exportedAt: string; itemCounts: Record<string, number> },
): Promise<{ recorded: true }> {
  await getAgentById(agentId)
  console.info('agent.exported', { agentId, ...payload })
  return { recorded: true }
}
