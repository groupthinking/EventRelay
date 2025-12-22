#!/usr/bin/env node
import { spawn } from 'child_process';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';

async function main() {
  // Start the MCP server as a child process
  const serverProcess = spawn('node', ['index.js'], {
    stdio: ['pipe', 'pipe', 'pipe']
  });

  // Log server output
  serverProcess.stdout.on('data', (data) => {
    console.log(`Server stdout: ${data}`);
  });

  serverProcess.stderr.on('data', (data) => {
    console.log(`Server stderr: ${data}`);
  });

  // Give the server a moment to start
  await new Promise(resolve => setTimeout(resolve, 2000));

  // Connect to the server
  const transport = new StdioClientTransport(serverProcess.stdin, serverProcess.stdout);
  const client = new Client();
  
  try {
    await client.connect(transport);
    console.log('Connected to MCP server');

    // List available tools
    const tools = await client.listTools();
    console.log('Available tools:', tools);

    // Test the calculate tool
    if (tools.tools.some(tool => tool.name === 'calculate')) {
      console.log('Testing calculate tool...');
      const result = await client.callTool('calculate', {
        operation: 'add',
        a: 42,
        b: 58
      });
      console.log('Calculate result:', result);
    }

    // Test the transform_text tool
    if (tools.tools.some(tool => tool.name === 'transform_text')) {
      console.log('Testing transform_text tool...');
      const result = await client.callTool('transform_text', {
        text: 'hello world',
        transformation: 'uppercase'
      });
      console.log('Transform result:', result);
    }

    // List available prompts
    const prompts = await client.listPrompts();
    console.log('Available prompts:', prompts);

    // Test the greeting prompt
    if (prompts.prompts.some(prompt => prompt.name === 'greeting')) {
      console.log('Testing greeting prompt...');
      const result = await client.renderPrompt('greeting', {
        name: 'User',
        time_of_day: 'evening'
      });
      console.log('Greeting result:', result);
    }

  } catch (error) {
    console.error('Error:', error);
  } finally {
    // Close the connection and terminate the server
    await client.close();
    serverProcess.kill();
    console.log('Test completed');
  }
}

main().catch(console.error);
