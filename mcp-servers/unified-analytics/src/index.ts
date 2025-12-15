#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import EventEmitter from 'events';
import { MetricsCollector } from './metrics/collector.js';
import { DataNormalizer } from './processing/normalizer.js';
import { EventBus } from './core/eventBus.js';
import { StorageMetrics } from './collectors/storage.js';
import { MemoryPathMetrics } from './collectors/memoryPath.js';

class UnifiedAnalyticsServer {
  private server: Server;
  private eventBus: EventBus;
  private metricsCollector: MetricsCollector;
  private dataNormalizer: DataNormalizer;

  constructor() {
    this.server = new Server(
      {
        name: 'unified-analytics-server',
        version: '0.1.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.eventBus = new EventBus();
    this.metricsCollector = new MetricsCollector(this.eventBus);
    this.dataNormalizer = new DataNormalizer();

    this.setupEventHandlers();
    this.setupToolHandlers();
    
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  private setupEventHandlers() {
    this.eventBus.on('metrics:collected', (data) => {
      const normalizedData = this.dataNormalizer.normalize(data);
      this.eventBus.emit('metrics:normalized', normalizedData);
    });
  }

  private setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'collect_unified_metrics',
          description: 'Collect metrics from all integrated sources',
          inputSchema: {
            type: 'object',
            properties: {
              sources: {
                type: 'array',
                items: {
                  type: 'string',
                  enum: ['memory-path', 'storage', 'all']
                },
                description: 'Sources to collect metrics from'
              },
              timeRange: {
                type: 'object',
                properties: {
                  start: {
                    type: 'string',
                    format: 'date-time'
                  },
                  end: {
                    type: 'string',
                    format: 'date-time'
                  }
                }
              }
            },
            required: ['sources']
          }
        },
        {
          name: 'get_unified_analysis',
          description: 'Get analyzed and correlated metrics',
          inputSchema: {
            type: 'object',
            properties: {
              metricTypes: {
                type: 'array',
                items: {
                  type: 'string',
                  enum: ['performance', 'usage', 'patterns', 'all']
                }
              },
              format: {
                type: 'string',
                enum: ['json', 'graph'],
                default: 'json'
              }
            },
            required: ['metricTypes']
          }
        }
      ]
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      try {
        switch (request.params.name) {
          case 'collect_unified_metrics': {
            const { sources, timeRange } = request.params.arguments as {
              sources: string[];
              timeRange?: { start: string; end: string };
            };

            const metrics = await this.metricsCollector.collect(sources, timeRange);
            
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(metrics, null, 2)
                }
              ]
            };
          }

          case 'get_unified_analysis': {
            const { metricTypes, format = 'json' } = request.params.arguments as {
              metricTypes: string[];
              format?: 'json' | 'graph';
            };

            const analysis = await this.metricsCollector.analyze(metricTypes);

            if (format === 'graph') {
              // Convert analysis to Mermaid graph format
              const mermaid = ['graph TD'];
              Object.entries(analysis).forEach(([key, value], index) => {
                mermaid.push(`  ${index}_${key.replace(/\W+/g, '_')} --> ${value}`);
              });

              return {
                content: [
                  {
                    type: 'text',
                    text: mermaid.join('\n')
                  }
                ]
              };
            }

            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(analysis, null, 2)
                }
              ]
            };
          }

          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${request.params.name}`
            );
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
        return {
          content: [
            {
              type: 'text',
              text: `Error: ${errorMessage}`
            }
          ],
          isError: true
        };
      }
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Unified Analytics MCP server running on stdio');
  }
}

const server = new UnifiedAnalyticsServer();
server.run().catch(console.error);
