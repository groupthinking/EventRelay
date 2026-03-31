/**
 * LiquidAI LFM2-VL MCP Connector
 *
 * Connects to the LiquidAI LFM2 MCP server at
 * https://liquidai-lfm2-mcp.static.hf.space
 *
 * LFM2-VL is LiquidAI's vision-language model that supports both text
 * generation and image/video understanding tasks via a standard MCP
 * HTTP transport.
 */

/**
 * LiquidAI connector configuration
 */
export interface LiquidAIConfig {
  /** Base URL of the LFM2 MCP server. Defaults to the public HF Space endpoint. */
  baseUrl?: string;
  /** Optional bearer token for authenticated deployments. */
  apiKey?: string;
  /** Request timeout in milliseconds. Defaults to 60_000. */
  timeoutMs?: number;
}

/**
 * Available LFM2-VL tool names
 */
export type LiquidAIToolName =
  | 'generate_text'
  | 'analyze_vision'
  | 'chat_completion'
  | 'list_tools';

/** Input schemas for each LFM2 tool */
export interface LiquidAIToolArguments {
  generate_text: {
    prompt: string;
    max_tokens?: number;
    temperature?: number;
    system?: string;
  };
  analyze_vision: {
    prompt: string;
    /** Base-64 encoded image or URL */
    image: string;
    max_tokens?: number;
  };
  chat_completion: {
    messages: Array<{ role: 'user' | 'assistant' | 'system'; content: string }>;
    max_tokens?: number;
    temperature?: number;
  };
  list_tools: Record<string, never>;
}

/** JSON-RPC request envelope used by the MCP HTTP transport */
interface MCPRequest {
  jsonrpc: '2.0';
  id: string | number;
  method: string;
  params?: Record<string, unknown>;
}

/** JSON-RPC response envelope */
interface MCPResponse<T = unknown> {
  jsonrpc: '2.0';
  id: string | number;
  result?: T;
  error?: { code: number; message: string; data?: unknown };
}

/**
 * MCP Connector for LiquidAI LFM2-VL
 *
 * Wraps the public Hugging Face Space MCP endpoint and exposes the
 * model's capabilities as typed MCP tool calls.
 */
export class LiquidAIConnector {
  private readonly baseUrl: string;
  private readonly apiKey: string | undefined;
  private readonly timeoutMs: number;
  private requestId = 0;

  constructor(config: LiquidAIConfig = {}) {
    this.baseUrl = (config.baseUrl ?? 'https://liquidai-lfm2-mcp.static.hf.space').replace(/\/$/, '');
    this.apiKey = config.apiKey;
    this.timeoutMs = config.timeoutMs ?? 60_000;
  }

  /**
   * List available tools with their JSON schemas.
   * Combines locally known schemas with whatever the server exposes.
   */
  async listTools() {
    return {
      tools: [
        {
          name: 'generate_text',
          description: 'Generate text using LiquidAI LFM2-VL',
          inputSchema: {
            type: 'object',
            properties: {
              prompt: { type: 'string', description: 'Input prompt for the model' },
              max_tokens: { type: 'number', default: 512, description: 'Maximum tokens to generate' },
              temperature: { type: 'number', default: 0.7, description: 'Sampling temperature (0-2)' },
              system: { type: 'string', description: 'Optional system prompt' },
            },
            required: ['prompt'],
          },
        },
        {
          name: 'analyze_vision',
          description: 'Analyze an image or video frame using LFM2-VL vision capabilities',
          inputSchema: {
            type: 'object',
            properties: {
              prompt: { type: 'string', description: 'Question or instruction for the image' },
              image: {
                type: 'string',
                description: 'Base-64 encoded image data or a public image URL',
              },
              max_tokens: { type: 'number', default: 512 },
            },
            required: ['prompt', 'image'],
          },
        },
        {
          name: 'chat_completion',
          description: 'Multi-turn chat completion with LFM2-VL',
          inputSchema: {
            type: 'object',
            properties: {
              messages: {
                type: 'array',
                items: {
                  type: 'object',
                  properties: {
                    role: { type: 'string', enum: ['user', 'assistant', 'system'] },
                    content: { type: 'string' },
                  },
                  required: ['role', 'content'],
                },
              },
              max_tokens: { type: 'number', default: 512 },
              temperature: { type: 'number', default: 0.7 },
            },
            required: ['messages'],
          },
        },
        {
          name: 'list_tools',
          description: 'List available tools exposed by the LFM2 MCP server',
          inputSchema: { type: 'object', properties: {} },
        },
      ],
    };
  }

  /**
   * Execute a named tool against the LFM2 MCP server.
   */
  async executeTool<T extends LiquidAIToolName>(
    name: T,
    args: LiquidAIToolArguments[T],
  ): Promise<unknown> {
    try {
      switch (name) {
        case 'generate_text':
          return await this.generateText(args as LiquidAIToolArguments['generate_text']);
        case 'analyze_vision':
          return await this.analyzeVision(args as LiquidAIToolArguments['analyze_vision']);
        case 'chat_completion':
          return await this.chatCompletion(args as LiquidAIToolArguments['chat_completion']);
        case 'list_tools':
          return await this.listTools();
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error(`[LiquidAIConnector] Error executing tool "${name}":`, msg);
      throw new Error(`LFM2 MCP operation failed: ${msg}`);
    }
  }

  // ------------------------------------------------------------------
  // Private helpers
  // ------------------------------------------------------------------

  private async generateText(args: LiquidAIToolArguments['generate_text']): Promise<unknown> {
    return this.callMCP('tools/call', {
      name: 'generate_text',
      arguments: {
        prompt: args.prompt,
        max_tokens: args.max_tokens ?? 512,
        temperature: args.temperature ?? 0.7,
        ...(args.system ? { system: args.system } : {}),
      },
    });
  }

  private async analyzeVision(args: LiquidAIToolArguments['analyze_vision']): Promise<unknown> {
    return this.callMCP('tools/call', {
      name: 'analyze_vision',
      arguments: {
        prompt: args.prompt,
        image: args.image,
        max_tokens: args.max_tokens ?? 512,
      },
    });
  }

  private async chatCompletion(args: LiquidAIToolArguments['chat_completion']): Promise<unknown> {
    return this.callMCP('tools/call', {
      name: 'chat_completion',
      arguments: {
        messages: args.messages,
        max_tokens: args.max_tokens ?? 512,
        temperature: args.temperature ?? 0.7,
      },
    });
  }

  /**
   * Send a JSON-RPC 2.0 request to the LFM2 MCP HTTP endpoint.
   */
  private async callMCP(method: string, params?: Record<string, unknown>): Promise<unknown> {
    const id = ++this.requestId;
    const body: MCPRequest = {
      jsonrpc: '2.0',
      id,
      method,
      ...(params ? { params } : {}),
    };

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}/mcp`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timer);
    }

    if (!response.ok) {
      const text = await response.text().catch(() => response.statusText);
      throw new Error(`LFM2 MCP HTTP ${response.status}: ${text}`);
    }

    const json: MCPResponse = await response.json();
    if (json.error) {
      throw new Error(`LFM2 MCP error ${json.error.code}: ${json.error.message}`);
    }
    return json.result;
  }
}
