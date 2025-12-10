#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import puppeteer from 'puppeteer';
import dotenv from 'dotenv';

dotenv.config();

const GROK_EMAIL = process.env.GROK_EMAIL;
const GROK_PASSWORD = process.env.GROK_PASSWORD;

if (!GROK_EMAIL || !GROK_PASSWORD) {
  throw new Error('GROK_EMAIL and GROK_PASSWORD environment variables are required');
}

interface GrokSession {
  browser: puppeteer.Browser;
  page: puppeteer.Page;
  isAuthenticated: boolean;
}

class GrokServer {
  private server: Server;
  private session: GrokSession | null = null;

  constructor() {
    this.server = new Server(
      {
        name: 'grok-server',
        version: '0.1.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    process.on('SIGINT', async () => {
      await this.cleanup();
      process.exit(0);
    });
  }

  private async initSession(): Promise<GrokSession> {
    if (this.session?.isAuthenticated) {
      return this.session;
    }

    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();

    // Navigate to Grok and authenticate
    await page.goto('https://grok.x.ai');
    await page.waitForSelector('input[type="email"]');
    await page.type('input[type="email"]', GROK_EMAIL);
    await page.type('input[type="password"]', GROK_PASSWORD);
    await page.click('button[type="submit"]');
    
    // Wait for authentication to complete
    await page.waitForNavigation();

    this.session = { browser, page, isAuthenticated: true };
    return this.session;
  }

  private async cleanup() {
    if (this.session?.browser) {
      await this.session.browser.close();
    }
    await this.server.close();
  }

  private setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'execute_code',
          description: 'Execute code using Grok and return the result',
          inputSchema: {
            type: 'object',
            properties: {
              code: {
                type: 'string',
                description: 'The code to execute',
              },
              language: {
                type: 'string',
                description: 'Programming language of the code',
              },
            },
            required: ['code', 'language'],
          },
        },
        {
          name: 'web_interaction',
          description: 'Ask Grok to interact with web content',
          inputSchema: {
            type: 'object',
            properties: {
              url: {
                type: 'string',
                description: 'URL of the webpage to interact with',
              },
              task: {
                type: 'string',
                description: 'Task to perform with the webpage content',
              },
            },
            required: ['url', 'task'],
          },
        },
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const session = await this.initSession();

      try {
        switch (request.params.name) {
          case 'execute_code': {
            const { code, language } = request.params.arguments as { code: string; language: string };
            
            // Navigate to code execution interface
            await session.page.goto('https://grok.x.ai/chat');
            await session.page.waitForSelector('textarea');
            
            // Format code execution request
            const prompt = `Execute this ${language} code and show the result:\n\`\`\`${language}\n${code}\n\`\`\``;
            await session.page.type('textarea', prompt);
            await session.page.keyboard.press('Enter');
            
            // Wait for and extract response
            await session.page.waitForSelector('.response-content');
            const response = await session.page.$eval('.response-content', el => el.textContent);

            return {
              content: [
                {
                  type: 'text',
                  text: response || 'No response received',
                },
              ],
            };
          }

          case 'web_interaction': {
            const { url, task } = request.params.arguments as { url: string; task: string };
            
            // Navigate to chat interface
            await session.page.goto('https://grok.x.ai/chat');
            await session.page.waitForSelector('textarea');
            
            // Format web interaction request
            const prompt = `Visit this URL: ${url}\nThen ${task}`;
            await session.page.type('textarea', prompt);
            await session.page.keyboard.press('Enter');
            
            // Wait for and extract response
            await session.page.waitForSelector('.response-content');
            const response = await session.page.$eval('.response-content', el => el.textContent);

            return {
              content: [
                {
                  type: 'text',
                  text: response || 'No response received',
                },
              ],
            };
          }

          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${request.params.name}`
            );
        }
      } catch (error) {
        console.error('Tool execution error:', error);
        return {
          content: [
            {
              type: 'text',
              text: `Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Grok MCP server running on stdio');
  }
}

const server = new GrokServer();
server.run().catch(console.error);
