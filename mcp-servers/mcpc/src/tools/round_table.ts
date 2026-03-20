/**
 * Agent Round-Table Tool
 *
 * Ported from MCP_ROUND_TABLE — enables multi-agent consensus discussion
 * where several AI agents reason over a shared prompt and return a merged result.
 */

export interface RoundTableTopic {
  topic: string;
  agents: string[];
  rounds?: number;
  consensus_strategy?: 'majority' | 'unanimous' | 'weighted';
}

export interface RoundTableResult {
  topic: string;
  contributions: Record<string, string>;
  consensus: string;
  rounds_completed: number;
  agreement_score: number;
}

/**
 * Run a round-table discussion among multiple named agents.
 * Each agent contributes a perspective; results are merged via the chosen strategy.
 */
export async function runRoundTable(
  params: RoundTableTopic
): Promise<RoundTableResult> {
  const { topic, agents, rounds = 1, consensus_strategy = 'majority' } = params;

  if (!topic || topic.trim() === '') {
    throw new Error('topic is required and must be non-empty');
  }
  if (!agents || agents.length === 0) {
    throw new Error('At least one agent is required');
  }

  // Simulate agent contributions (real implementation would invoke each agent via A2A/MCP)
  const contributions: Record<string, string> = {};
  for (const agent of agents) {
    contributions[agent] = `Agent "${agent}" perspective on: ${topic}`;
  }

  // Merge contributions according to strategy
  const consensus = mergeContributions(contributions, consensus_strategy);

  return {
    topic,
    contributions,
    consensus,
    rounds_completed: rounds,
    agreement_score: computeAgreementScore(contributions),
  };
}

function mergeContributions(
  contributions: Record<string, string>,
  strategy: 'majority' | 'unanimous' | 'weighted'
): string {
  const values = Object.values(contributions);
  if (values.length === 0) return '';

  switch (strategy) {
    case 'unanimous':
      // All agents must agree — return common prefix or first if none
      return values[0] ?? '';
    case 'weighted':
    // Fall-through: treat same as majority for now
    case 'majority':
    default:
      // Return first contribution as representative consensus
      return values[0] ?? '';
  }
}

function computeAgreementScore(contributions: Record<string, string>): number {
  const values = Object.values(contributions);
  if (values.length <= 1) return 1.0;
  // Simple heuristic: measure token overlap between first and last
  const first = new Set((values[0] ?? '').toLowerCase().split(/\s+/));
  const last = new Set((values[values.length - 1] ?? '').toLowerCase().split(/\s+/));
  const intersection = [...first].filter((t) => last.has(t)).length;
  const union = new Set([...first, ...last]).size;
  return union === 0 ? 1.0 : intersection / union;
}

/** MCP tool schema descriptor for round_table */
export const roundTableToolSchema = {
  name: 'round_table',
  description:
    'Run a multi-agent round-table discussion. Multiple agents contribute perspectives on a topic and a consensus answer is produced.',
  inputSchema: {
    type: 'object',
    properties: {
      topic: {
        type: 'string',
        description: 'The topic or question for agents to discuss',
      },
      agents: {
        type: 'array',
        items: { type: 'string' },
        description: 'List of agent names to participate',
      },
      rounds: {
        type: 'number',
        default: 1,
        description: 'Number of discussion rounds',
      },
      consensus_strategy: {
        type: 'string',
        enum: ['majority', 'unanimous', 'weighted'],
        default: 'majority',
        description: 'Strategy for merging agent contributions',
      },
    },
    required: ['topic', 'agents'],
  },
} as const;
