#!/usr/bin/env node
import { genkit, z } from 'genkit';
import { mcpServer } from 'genkitx-mcp';

// Create a Genkit instance
const ai = genkit({});

// Define a simple calculator tool
ai.defineTool(
  {
    name: 'calculate',
    description: 'Perform basic arithmetic operations',
    inputSchema: z.object({ 
      operation: z.enum(['add', 'subtract', 'multiply', 'divide']),
      a: z.number(), 
      b: z.number() 
    }),
    outputSchema: z.number(),
  },
  async ({ operation, a, b }) => {
    switch (operation) {
      case 'add':
        return a + b;
      case 'subtract':
        return a - b;
      case 'multiply':
        return a * b;
      case 'divide':
        if (b === 0) throw new Error('Cannot divide by zero');
        return a / b;
      default:
        throw new Error(`Unknown operation: ${operation}`);
    }
  }
);

// Define a text transformation tool
ai.defineTool(
  {
    name: 'transform_text',
    description: 'Transform text using various operations',
    inputSchema: z.object({ 
      text: z.string(),
      transformation: z.enum(['uppercase', 'lowercase', 'capitalize', 'reverse'])
    }),
    outputSchema: z.string(),
  },
  async ({ text, transformation }) => {
    switch (transformation) {
      case 'uppercase':
        return text.toUpperCase();
      case 'lowercase':
        return text.toLowerCase();
      case 'capitalize':
        return text.split(' ')
          .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
          .join(' ');
      case 'reverse':
        return text.split('').reverse().join('');
      default:
        throw new Error(`Unknown transformation: ${transformation}`);
    }
  }
);

// Define a greeting prompt
ai.definePrompt(
  {
    name: 'greeting',
    description: 'Generate a friendly greeting',
    input: {
      schema: z.object({ 
        name: z.string(),
        time_of_day: z.enum(['morning', 'afternoon', 'evening', 'night']).optional()
      }),
      default: { time_of_day: 'morning' }
    },
  },
  `Good {{time_of_day}}, {{name}}! How can I assist you today?`
);

// Start the MCP server
const server = mcpServer(ai, { 
  name: 'genkit_demo_server', 
  version: '1.0.0' 
});

console.error('Starting Genkit MCP server...');
server.start();
