#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import puppeteer, { Browser, Page } from 'puppeteer';
import dotenv from 'dotenv';
import { McpError, ErrorCode } from '@modelcontextprotocol/sdk/types.js';

dotenv.config();

const GROK_EMAIL = process.env.GROK_EMAIL;
const GROK_PASSWORD = process.env.GROK_PASSWORD;

if (!GROK_EMAIL || !GROK_PASSWORD) {
  throw new Error('GROK_EMAIL and GROK_PASSWORD environment variables are required');
}

interface GrokSession {
  browser: Browser;
  page: Page;
  isAuthenticated: boolean;
}

class GrokSessionManager {
  private session: GrokSession | null = null;

  async getSession(): Promise<GrokSession> {
    if (this.session?.isAuthenticated) {
      return this.session;
    }

    const browser = await puppeteer.launch({ 
      headless: process.env.HEADLESS !== 'false',
      defaultViewport: null,
      args: ['--start-maximized'] // Optional: makes it easier to see
    });
    const page = await browser.newPage();

    // Navigate to Grok and authenticate
    await page.goto('https://grok.x.ai');
    await page.waitForSelector('input[type="email"]');
    await page.type('input[type="email"]', GROK_EMAIL as string);
    await page.type('input[type="password"]', GROK_PASSWORD as string);
    await page.click('button[type="submit"]');
    
    // Wait for authentication to complete
    await page.waitForNavigation();

    this.session = { browser, page, isAuthenticated: true };
    return this.session;
  }

  async close() {
    if (this.session?.browser) {
      await this.session.browser.close();
      this.session = null;
    }
  }
}

const sessionManager = new GrokSessionManager();

const server = new McpServer({
  name: 'grok-server',
  version: '0.1.0',
});

server.tool(
  'execute_code',
  {
    code: z.string().describe('The code to execute'),
    language: z.string().describe('Programming language of the code'),
  },
  async ({ code, language }) => {
    try {
      const session = await sessionManager.getSession();
      
      // Navigate to code execution interface
      await session.page.goto('https://grok.x.ai/chat');
      await session.page.waitForSelector('textarea');
      
      // Format code execution request
      const prompt = `Execute this ${language} code and show the result:\n\`\`\`${language}\n${code}\n\`\`\``;
      await session.page.type('textarea', prompt);
      await session.page.keyboard.press('Enter');
      
      // Wait for and extract response
      await session.page.waitForSelector('.response-content');
      const response = await session.page.$eval('.response-content', (el: any) => el.textContent);

      return {
        content: [
          {
            type: 'text',
            text: response || 'No response received',
          },
        ],
      };
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
  }
);

server.tool(
  'web_interaction',
  {
    url: z.string().describe('URL of the webpage to interact with'),
    task: z.string().describe('Task to perform with the webpage content'),
  },
  async ({ url, task }) => {
    try {
      const session = await sessionManager.getSession();

      // Navigate to chat interface
      await session.page.goto('https://grok.x.ai/chat');
      await session.page.waitForSelector('textarea');
      
      // Format web interaction request
      const prompt = `Visit this URL: ${url}\nThen ${task}`;
      await session.page.type('textarea', prompt);
      await session.page.keyboard.press('Enter');
      
      // Wait for and extract response
      await session.page.waitForSelector('.response-content');
      const response = await session.page.$eval('.response-content', (el: any) => el.textContent);

      return {
        content: [
          {
            type: 'text',
            text: response || 'No response received',
          },
        ],
      };
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
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Grok MCP server running on stdio');
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});

// Handle cleanup
// Handle cleanup
const cleanup = async () => {
  await sessionManager.close();
  process.exit(0);
};

process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);
