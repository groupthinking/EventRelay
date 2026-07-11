#!/usr/bin/env node
import { Client } from '@modelcontextprotocol/sdk/client';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

async function main() {
  const transport = new StdioClientTransport({
    command: 'node',
    args: ['tools/mcp/git_workflow_server.mjs'],
    env: {
      ...process.env,
      GIT_WORKSPACE_ROOT: process.env.GIT_WORKSPACE_ROOT ?? process.cwd(),
      GIT_DEFAULT_REMOTE: process.env.GIT_DEFAULT_REMOTE ?? 'origin',
    },
  });

  const client = new Client(
    {
      name: 'git-workflow-test-client',
      version: '1.0.0',
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  await client.connect(transport);

  const tools = await client.listTools();
  console.log('Available tools:', tools.tools.map((tool) => tool.name));

  const status = await client.callTool({ name: 'git_status', arguments: {} });
  console.log('git_status result:\n', status.content.map((entry) => entry.text).join('\n'));

  await client.close();
}

main().catch((error) => {
  console.error('Test client failed:', error);
  process.exit(1);
});
