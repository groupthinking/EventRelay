#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  McpError,
  ReadResourceRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import puppeteer from 'puppeteer';

class PuppeteerServer {
  constructor() {
    this.server = new Server(
      {
        name: 'puppeteer-server',
        version: '0.1.0',
      },
      {
        capabilities: {
          resources: {},
          tools: {},
        },
      }
    );

    this.browser = null;
    this.page = null;
    this.setupHandlers();
  }

  async setupBrowser() {
    if (!this.browser) {
      this.browser = await puppeteer.launch({ headless: false });
      this.page = await this.browser.newPage();
    }
  }

  setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'puppeteer_navigate',
          description: 'Navigate to any URL in the browser',
          inputSchema: {
            type: 'object',
            properties: {
              url: {
                type: 'string',
                description: 'URL to navigate to',
              },
            },
            required: ['url'],
          },
        },
        {
          name: 'puppeteer_screenshot',
          description: 'Capture screenshots of the entire page or specific elements',
          inputSchema: {
            type: 'object',
            properties: {
              name: {
                type: 'string',
                description: 'Name for the screenshot',
              },
              selector: {
                type: 'string',
                description: 'CSS selector for element to screenshot',
              },
              width: {
                type: 'number',
                description: 'Screenshot width',
                default: 800,
              },
              height: {
                type: 'number',
                description: 'Screenshot height',
                default: 600,
              },
            },
            required: ['name'],
          },
        },
        {
          name: 'puppeteer_click',
          description: 'Click elements on the page',
          inputSchema: {
            type: 'object',
            properties: {
              selector: {
                type: 'string',
                description: 'CSS selector for element to click',
              },
            },
            required: ['selector'],
          },
        },
        {
          name: 'puppeteer_hover',
          description: 'Hover elements on the page',
          inputSchema: {
            type: 'object',
            properties: {
              selector: {
                type: 'string',
                description: 'CSS selector for element to hover',
              },
            },
            required: ['selector'],
          },
        },
        {
          name: 'puppeteer_fill',
          description: 'Fill out input fields',
          inputSchema: {
            type: 'object',
            properties: {
              selector: {
                type: 'string',
                description: 'CSS selector for input field',
              },
              value: {
                type: 'string',
                description: 'Value to fill',
              },
            },
            required: ['selector', 'value'],
          },
        },
        {
          name: 'puppeteer_select',
          description: 'Select an element with SELECT tag',
          inputSchema: {
            type: 'object',
            properties: {
              selector: {
                type: 'string',
                description: 'CSS selector for element to select',
              },
              value: {
                type: 'string',
                description: 'Value to select',
              },
            },
            required: ['selector', 'value'],
          },
        },
        {
          name: 'puppeteer_evaluate',
          description: 'Execute JavaScript in the browser console',
          inputSchema: {
            type: 'object',
            properties: {
              script: {
                type: 'string',
                description: 'JavaScript code to execute',
              },
            },
            required: ['script'],
          },
        },
      ],
    }));

    this.server.setRequestHandler(ListResourcesRequestSchema, async () => ({
      resources: [
        {
          uri: 'console://logs',
          name: 'Browser Console Logs',
          mimeType: 'text/plain',
          description: 'Browser console output in text format',
        },
      ],
    }));

    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      if (request.params.uri === 'console://logs' && this.page) {
        return {
          contents: [
            {
              uri: request.params.uri,
              mimeType: 'text/plain',
              text: await this.page.evaluate(() => {
                return window.consoleLog || '';
              }),
            },
          ],
        };
      }

      if (request.params.uri.startsWith('screenshot://')) {
        const name = request.params.uri.replace('screenshot://', '');
        // Return the screenshot if it exists
        return {
          contents: [
            {
              uri: request.params.uri,
              mimeType: 'image/png',
              // You would need to implement screenshot storage and retrieval
              text: `Screenshot ${name}`,
            },
          ],
        };
      }

      throw new McpError(
        ErrorCode.ResourceNotFound,
        `Resource not found: ${request.params.uri}`
      );
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      await this.setupBrowser();

      switch (request.params.name) {
        case 'puppeteer_navigate':
          await this.page.goto(request.params.arguments.url);
          return { content: [{ type: 'text', text: 'Navigation complete' }] };

        case 'puppeteer_screenshot':
          const { name, selector, width = 800, height = 600 } =
            request.params.arguments;
          await this.page.setViewport({ width, height });
          
          if (selector) {
            const element = await this.page.$(selector);
            if (!element) {
              throw new McpError(
                ErrorCode.InvalidParams,
                `Element not found: ${selector}`
              );
            }
            await element.screenshot({ path: `${name}.png` });
          } else {
            await this.page.screenshot({ path: `${name}.png` });
          }
          return {
            content: [{ type: 'text', text: `Screenshot saved as ${name}.png` }],
          };

        case 'puppeteer_click':
          await this.page.click(request.params.arguments.selector);
          return { content: [{ type: 'text', text: 'Click performed' }] };

        case 'puppeteer_hover':
          await this.page.hover(request.params.arguments.selector);
          return { content: [{ type: 'text', text: 'Hover performed' }] };

        case 'puppeteer_fill':
          await this.page.type(
            request.params.arguments.selector,
            request.params.arguments.value
          );
          return { content: [{ type: 'text', text: 'Input field filled' }] };

        case 'puppeteer_select':
          await this.page.select(
            request.params.arguments.selector,
            request.params.arguments.value
          );
          return { content: [{ type: 'text', text: 'Selection made' }] };

        case 'puppeteer_evaluate':
          const result = await this.page.evaluate(
            request.params.arguments.script
          );
          return {
            content: [
              {
                type: 'text',
                text: `Script executed. Result: ${JSON.stringify(result)}`,
              },
            ],
          };

        default:
          throw new McpError(
            ErrorCode.MethodNotFound,
            `Unknown tool: ${request.params.name}`
          );
      }
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Puppeteer MCP server running on stdio');
  }
}

const server = new PuppeteerServer();
server.run().catch(console.error);
