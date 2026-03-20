/**
 * MCPC Orchestrator
 *
 * Routes incoming tool calls to the appropriate handler.
 * This is the single point of truth for all MCP tool dispatch.
 */

import { runRoundTable } from './tools/round_table.js';
import {
  listTools,
  executeToolChain,
  type ToolChainStep,
} from './tools/tool_manager.js';
import {
  setState,
  getState,
  deleteState,
  listStateKeys,
} from './tools/shared_state.js';

export interface OrchestratorResult {
  content: Array<{ type: 'text'; text: string }>;
  isError?: boolean;
}

/**
 * Dispatch a tool call to its handler and return an MCP-formatted result.
 */
export async function dispatchTool(
  toolName: string,
  args: Record<string, unknown>
): Promise<OrchestratorResult> {
  try {
    let result: unknown;

    switch (toolName) {
      // ── Round-table ────────────────────────────────────────────────────────
      case 'round_table': {
        result = await runRoundTable({
          topic: args['topic'] as string,
          agents: args['agents'] as string[],
          rounds: args['rounds'] as number | undefined,
          consensus_strategy: args['consensus_strategy'] as
            | 'majority'
            | 'unanimous'
            | 'weighted'
            | undefined,
        });
        break;
      }

      // ── Tool manager ───────────────────────────────────────────────────────
      case 'list_tools': {
        result = listTools(args['tag'] as string | undefined);
        break;
      }

      case 'execute_tool_chain': {
        const steps = args['steps'] as ToolChainStep[];
        // Simple passthrough executor — real deployments would call registered servers
        result = await executeToolChain(steps, async (name, toolArgs) => {
          return dispatchTool(name, toolArgs);
        });
        break;
      }

      // ── Shared state ───────────────────────────────────────────────────────
      case 'state_set': {
        result = setState(
          args['key'] as string,
          args['value'],
          args['author'] as string | undefined
        );
        break;
      }

      case 'state_get': {
        const entry = getState(args['key'] as string);
        result = entry ?? { key: args['key'], value: null, found: false };
        break;
      }

      case 'state_list': {
        result = { keys: listStateKeys() };
        break;
      }

      case 'state_delete': {
        const deleted = deleteState(args['key'] as string);
        result = { key: args['key'], deleted };
        break;
      }

      default:
        return {
          content: [{ type: 'text', text: `Unknown tool: ${toolName}` }],
          isError: true,
        };
    }

    return {
      content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      content: [{ type: 'text', text: `Error in ${toolName}: ${message}` }],
      isError: true,
    };
  }
}
