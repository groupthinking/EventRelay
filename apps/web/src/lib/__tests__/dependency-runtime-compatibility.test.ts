import { createServer, type Server } from 'node:http';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { z } from 'zod';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';

const webRequire = createRequire(import.meta.url);
const rootRequire = createRequire(fileURLToPath(new URL('../../../../../package.json', import.meta.url)));
const servers: Server[] = [];

afterEach(async () => {
  await Promise.all(servers.splice(0).map((server) => new Promise<void>((resolve, reject) => {
    server.closeAllConnections();
    server.close((error) => error ? reject(error) : resolve());
  })));
});

async function localEndpoint() {
  const server = createServer((request, response) => {
    response.writeHead(200, { 'content-type': 'application/json' });
    response.end(JSON.stringify({ method: request.method, path: request.url }));
  });
  servers.push(server);
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('Local fixture did not bind a TCP port');
  return `http://127.0.0.1:${address.port}/receipt`;
}

describe('installed dependency consumer compatibility', () => {
  it('round-trips MCP tools and enforces Zod input validation before executing a handler', async () => {
    const server = new McpServer({ name: 'eventrelay-offline-regression', version: '1.0.0' });
    const handler = vi.fn(async ({ message }: { message: string }) => ({
      content: [{ type: 'text' as const, text: message.toUpperCase() }],
    }));
    server.registerTool('echo', {
      description: 'Local transport fixture; no provider or external service.',
      inputSchema: { message: z.string().min(1) },
    }, handler);
    const client = new Client({ name: 'eventrelay-offline-client', version: '1.0.0' });
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    try {
      await server.connect(serverTransport);
      await client.connect(clientTransport);
      const listing = await client.listTools();
      expect(listing.tools[0].inputSchema).toMatchObject({
        type: 'object', properties: { message: { type: 'string', minLength: 1 } }, required: ['message'],
      });
      expect(await client.callTool({ name: 'echo', arguments: { message: 'evidence' } }))
        .toMatchObject({ content: [{ type: 'text', text: 'EVIDENCE' }] });
      expect(await client.callTool({ name: 'echo', arguments: { message: 123 } }))
        .toMatchObject({ isError: true });
      expect(handler).toHaveBeenCalledTimes(1);
    } finally {
      await client.close();
      await server.close();
    }
  });

  it('loads Next native Sharp dependency and transforms real PNG bytes', async () => {
    const nextRequire = createRequire(webRequire.resolve('next'));
    const sharp = nextRequire('sharp') as typeof import('sharp').default;
    const source = await sharp({
      create: { width: 4, height: 4, channels: 4, background: { r: 20, g: 80, b: 160, alpha: 1 } },
    }).png().toBuffer();
    const resized = await sharp(source).resize(2, 2).png().toBuffer();
    expect(source.subarray(1, 4).toString()).toBe('PNG');
    expect(await sharp(resized).metadata()).toMatchObject({ format: 'png', width: 2, height: 2 });
  });

  it.each([
    ['root tools', () => rootRequire('undici')],
    ['web runtime', () => webRequire('undici')],
    ...['@ai-sdk/provider-utils', '@workflow/world-local', '@workflow/world-vercel', '@vercel/blob']
      .map((name) => [name, () => createRequire(webRequire.resolve(name))('undici')] as const),
  ] as const)('%s uses its own Undici Agent with a real loopback response', async (_name, load) => {
    // Resolve from the actual consumer so nested Undici 6/7 and root 8 all run.
    // This catches Agent/fetch class mismatches across hoisted dependency copies.
    const { Agent, fetch } = load() as typeof import('undici');
    const dispatcher = new Agent();
    try {
      const response = await fetch(await localEndpoint(), { dispatcher });
      expect(response.status).toBe(200);
      expect(await response.json()).toEqual({ method: 'GET', path: '/receipt' });
    } finally {
      await dispatcher.close();
    }
  });
});
