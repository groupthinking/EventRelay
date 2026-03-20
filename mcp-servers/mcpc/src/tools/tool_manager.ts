/**
 * Tool Manager
 *
 * Ported from mcp-tools-extension — manages tool registration, discovery,
 * and zero-glue chaining across multiple MCP servers.
 */

export interface RegisteredTool {
  name: string;
  description: string;
  server: string;
  inputSchema: Record<string, unknown>;
  tags: string[];
}

export interface ToolChainStep {
  tool: string;
  args: Record<string, unknown>;
  output_as?: string; // bind step output to this variable name for subsequent steps
}

export interface ToolChainResult {
  steps: Array<{ tool: string; result: unknown; duration_ms: number }>;
  final_output: unknown;
  variables: Record<string, unknown>;
}

/** In-memory tool registry */
const registry = new Map<string, RegisteredTool>();

/**
 * Register a tool in the central registry.
 */
export function registerTool(tool: RegisteredTool): void {
  if (!tool.name || tool.name.trim() === '') {
    throw new Error('Tool name is required');
  }
  registry.set(tool.name, tool);
}

/**
 * Unregister a tool.
 */
export function unregisterTool(name: string): boolean {
  return registry.delete(name);
}

/**
 * List all registered tools, optionally filtered by tag.
 */
export function listTools(tag?: string): RegisteredTool[] {
  const tools = [...registry.values()];
  if (tag) {
    return tools.filter((t) => t.tags.includes(tag));
  }
  return tools;
}

/**
 * Discover a tool by name.
 */
export function getTool(name: string): RegisteredTool | undefined {
  return registry.get(name);
}

/**
 * Execute a tool chain — each step can reference outputs from previous steps.
 * This enables zero-glue-code tool composition as described in the architecture doc.
 */
export async function executeToolChain(
  steps: ToolChainStep[],
  toolExecutor: (toolName: string, args: Record<string, unknown>) => Promise<unknown>
): Promise<ToolChainResult> {
  const results: ToolChainResult['steps'] = [];
  const variables: Record<string, unknown> = {};

  let lastOutput: unknown = undefined;

  for (const step of steps) {
    // Resolve any variable references in args
    const resolvedArgs = resolveArgs(step.args, variables);

    const start = Date.now();
    const result = await toolExecutor(step.tool, resolvedArgs);
    const duration_ms = Date.now() - start;

    results.push({ tool: step.tool, result, duration_ms });
    lastOutput = result;

    // Bind output to variable if requested
    if (step.output_as) {
      variables[step.output_as] = result;
    }
  }

  return { steps: results, final_output: lastOutput, variables };
}

/**
 * Resolve variable references like `$varName` in args values.
 */
function resolveArgs(
  args: Record<string, unknown>,
  variables: Record<string, unknown>
): Record<string, unknown> {
  const resolved: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(args)) {
    if (typeof value === 'string' && value.startsWith('$')) {
      const varName = value.slice(1);
      resolved[key] = variables[varName] ?? value;
    } else {
      resolved[key] = value;
    }
  }
  return resolved;
}

/** MCP tool schema descriptors */
export const toolManagerSchemas = [
  {
    name: 'list_tools',
    description: 'List all tools registered in the MCPC orchestrator, optionally filtered by tag.',
    inputSchema: {
      type: 'object',
      properties: {
        tag: {
          type: 'string',
          description: 'Optional tag to filter tools',
        },
      },
    },
  },
  {
    name: 'execute_tool_chain',
    description:
      'Execute a chain of tools in sequence with optional variable binding between steps. Enables zero-glue-code tool composition.',
    inputSchema: {
      type: 'object',
      properties: {
        steps: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              tool: { type: 'string', description: 'Tool name to invoke' },
              args: { type: 'object', description: 'Arguments for the tool' },
              output_as: {
                type: 'string',
                description: 'Bind this step output to variable name for subsequent steps',
              },
            },
            required: ['tool', 'args'],
          },
          description: 'Ordered list of tool invocations',
        },
      },
      required: ['steps'],
    },
  },
] as const;
