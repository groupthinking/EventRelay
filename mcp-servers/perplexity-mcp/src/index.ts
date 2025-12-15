#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';
import { Database } from 'better-sqlite3';

const PERPLEXITY_API_KEY = process.env.PERPLEXITY_API_KEY;
if (!PERPLEXITY_API_KEY) {
  throw new Error('PERPLEXITY_API_KEY environment variable is required');
}

interface PerplexityResponse {
  answer: string;
  context: string;
}

class PerplexityServer {
  private server: Server;
  private axiosInstance;
  constructor() {
    this.server = new Server(
      {
        name: 'perplexity-server',
        version: '0.1.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.axiosInstance = axios.create({
      baseURL: 'https://api.perplexity.ai/v1',
      headers: {
        'Authorization': `Bearer ${PERPLEXITY_API_KEY}`,
        'Content-Type': 'application/json',
      },
    });

    this.setupToolHandlers();
    
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  private setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'search',
          description: 'Perform a general search query to get comprehensive information on any topic',
          inputSchema: {
            type: 'object',
            properties: {
              query: {
                type: 'string',
                description: 'The search query or question',
              },
              detail_level: {
                type: 'string',
                enum: ['brief', 'normal', 'detailed'],
                description: 'Desired level of detail',
                default: 'normal',
              },
            },
            required: ['query'],
          },
        },
        {
          name: 'get_documentation',
          description: 'Get documentation and usage examples for a specific technology, library, or API',
          inputSchema: {
            type: 'object',
            properties: {
              query: {
                type: 'string',
                description: 'The technology, library, or API to get documentation for',
              },
              context: {
                type: 'string',
                description: 'Additional context about specific aspects to focus on',
              },
            },
            required: ['query'],
          },
        },
        {
          name: 'find_apis',
          description: 'Find and evaluate APIs that could be integrated into a project',
          inputSchema: {
            type: 'object',
            properties: {
              requirement: {
                type: 'string',
                description: 'The functionality or requirement you\'re looking to fulfill',
              },
              context: {
                type: 'string',
                description: 'Additional context about the project or specific needs',
              },
            },
            required: ['requirement'],
          },
        },
        {
          name: 'check_deprecated_code',
          description: 'Check if code or dependencies might be using deprecated features',
          inputSchema: {
            type: 'object',
            properties: {
              code: {
                type: 'string',
                description: 'The code snippet or dependency to check',
              },
              technology: {
                type: 'string',
                description: 'The technology or framework context (e.g., \'React\', \'Node.js\')',
              },
            },
            required: ['code'],
          },
        },
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      try {
        let prompt = '';
        let model = 'mixtral-8x7b-instruct';

        switch (request.params.name) {
          case 'search': {
            const { query, detail_level = 'normal' } = request.params.arguments as {
              query: string;
              detail_level?: 'brief' | 'normal' | 'detailed';
            };
            const detailPrompt = detail_level === 'brief' 
              ? 'Provide a concise summary' 
              : detail_level === 'detailed' 
                ? 'Provide detailed information including examples and references' 
                : 'Provide a balanced overview';
            prompt = `${detailPrompt} for the following query: ${query}`;
            break;
          }

          case 'get_documentation': {
            const { query, context } = request.params.arguments as {
              query: string;
              context?: string;
            };
            prompt = `Provide comprehensive documentation for ${query}${
              context ? ` focusing on ${context}` : ''
            }. Include best practices, common pitfalls, and usage examples.`;
            break;
          }

          case 'find_apis': {
            const { requirement, context } = request.params.arguments as {
              requirement: string;
              context?: string;
            };
            prompt = `Find and evaluate APIs that can fulfill this requirement: ${requirement}${
              context ? `. Context: ${context}` : ''
            }. For each API, include features, pricing, ease of integration, and pros/cons.`;
            break;
          }

          case 'check_deprecated_code': {
            const { code, technology } = request.params.arguments as {
              code: string;
              technology?: string;
            };
            prompt = `Analyze this code for deprecated features or patterns${
              technology ? ` in ${technology}` : ''
            }:\n\n${code}\n\nProvide specific details about deprecation status and migration guidance.`;
            break;
          }

          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${request.params.name}`
            );
        }

        const response = await this.axiosInstance.post('/chat/completions', {
          model,
          messages: [{ role: 'user', content: prompt }],
        });

        return {
          content: [
            {
              type: 'text',
              text: response.data.choices[0].message.content,
            },
          ],
        };
      } catch (error) {
        if (axios.isAxiosError(error)) {
          return {
            content: [
              {
                type: 'text',
                text: `Perplexity API error: ${
                  error.response?.data?.error?.message ?? error.message
                }`,
              },
            ],
            isError: true,
          };
        }
        throw error;
      }
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Perplexity MCP server running on stdio');
  }
}

const server = new PerplexityServer();
server.run().catch(console.error);
