#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError
} from '@modelcontextprotocol/sdk/types.js';
import Anthropic from '@anthropic-ai/sdk';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Initialize Anthropic client
const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY || ''
});

// Define tool schemas
const fermiEstimationSchema = {
  type: 'object',
  properties: {
    question: {
      type: 'string',
      description: 'The Fermi estimation question to answer'
    }
  },
  required: ['question']
};

const redTeamSchema = {
  type: 'object',
  properties: {
    prompt: {
      type: 'string',
      description: 'The prompt to analyze for potential risks'
    }
  },
  required: ['prompt']
};

class MetacognitionServer {
  private server: Server;

  constructor() {
    this.server = new Server(
      {
        name: 'metacognition-tools',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    
    // Error handling
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
          name: 'fermi_estimation',
          description: 'Perform a Fermi estimation to answer a quantitative question',
          inputSchema: fermiEstimationSchema,
        },
        {
          name: 'red_team',
          description: 'Analyze a prompt for potential risks and suggest improvements',
          inputSchema: redTeamSchema,
        },
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      switch (request.params.name) {
        case 'fermi_estimation':
          return this.handleFermiEstimation(request.params.arguments);
        case 'red_team':
          return this.handleRedTeam(request.params.arguments);
        default:
          throw new McpError(
            ErrorCode.MethodNotFound,
            `Unknown tool: ${request.params.name}`
          );
      }
    });
  }

  private async handleFermiEstimation(args: any) {
    if (typeof args !== 'object' || args === null || typeof args.question !== 'string') {
      throw new McpError(
        ErrorCode.InvalidParams,
        'Invalid Fermi estimation arguments'
      );
    }

    try {
      const response = await anthropic.messages.create({
        model: 'claude-3-opus-20240229',
        max_tokens: 1000,
        messages: [
          {
            role: 'user',
            content: `Perform a Fermi estimation to answer this question: ${args.question}
            
            Break down your reasoning step by step, showing all calculations and assumptions. 
            Provide a final numerical answer with appropriate units.`
          }
        ]
      });

      return {
        content: [
          {
            type: 'text',
            text: response.content[0].type === 'text' ? response.content[0].text : 'No text response received'
          }
        ]
      };
    } catch (error) {
      console.error('Anthropic API error:', error);
      return {
        content: [
          {
            type: 'text',
            text: `Error performing Fermi estimation: ${error instanceof Error ? error.message : String(error)}`
          }
        ],
        isError: true
      };
    }
  }

  private async handleRedTeam(args: any) {
    if (typeof args !== 'object' || args === null || typeof args.prompt !== 'string') {
      throw new McpError(
        ErrorCode.InvalidParams,
        'Invalid Red Team arguments'
      );
    }

    try {
      const response = await anthropic.messages.create({
        model: 'claude-3-opus-20240229',
        max_tokens: 1000,
        messages: [
          {
            role: 'user',
            content: `Act as a red team evaluator. Analyze this prompt for potential risks, harmful outputs, or ways it could be misused:
            
            "${args.prompt}"
            
            Identify specific vulnerabilities, suggest improvements to make it safer, and rate the overall risk level (Low, Medium, High).`
          }
        ]
      });

      return {
        content: [
          {
            type: 'text',
            text: response.content[0].type === 'text' ? response.content[0].text : 'No text response received'
          }
        ]
      };
    } catch (error) {
      console.error('Anthropic API error:', error);
      return {
        content: [
          {
            type: 'text',
            text: `Error performing Red Team analysis: ${error instanceof Error ? error.message : String(error)}`
          }
        ],
        isError: true
      };
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Metacognition Tools MCP server running on stdio');
  }
}

const server = new MetacognitionServer();
server.run().catch(console.error);
