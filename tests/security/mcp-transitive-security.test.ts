import { randomUUID } from 'node:crypto';
import { createServer } from 'node:http';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { describe, expect, expectTypeOf, it } from 'vitest';
import type { JsonSchemaType } from '@modelcontextprotocol/sdk/validation/types.js';

// Follow the actual optional-runtime GenAI -> MCP dependency chain. Importing
// a different workspace copy would conceal a vulnerable hoisted consumer.
const fromRoot = createRequire(fileURLToPath(new URL('../../package.json', import.meta.url)));
const fromGenai = createRequire(fromRoot.resolve('@google/genai'));
const fromSdk = createRequire(fromGenai.resolve('@modelcontextprotocol/sdk/client/index.js'));
const { Hono } = fromSdk('hono') as typeof import('hono');
const fromAjv = createRequire(fromSdk.resolve('ajv'));
const uri = fromAjv('fast-uri') as typeof import('fast-uri');

describe('installed MCP transitive security', () => {
  it.each(['node-server', 'hono'] as const)(
    '%s static middleware preserves public files without bypassing protected routes',
    async (adapter) => {
      const root = await mkdtemp(join(tmpdir(), 'eventrelay-static-security-'));
      try {
        await mkdir(join(root, 'static/admin'), { recursive: true });
        await writeFile(join(root, 'static/public.txt'), 'public fixture');
        await writeFile(join(root, 'static/admin/secret.txt'), 'private fixture');
        const app = new Hono();
        app.use('/static/admin/*', async (c) => c.text('Unauthorized', 401));
        if (adapter === 'node-server') {
          const { serveStatic } = fromSdk('@hono/node-server/serve-static') as
            typeof import('@hono/node-server/serve-static');
          app.use('/static/*', serveStatic({ root }));
        } else {
          const { serveStatic } = fromSdk('hono/serve-static') as
            typeof import('hono/serve-static');
          app.use('/static/*', serveStatic({ root, getContent: async (path) => {
            try { return await readFile(path); } catch { return null; }
          } }));
        }

        const publicFile = await app.request('http://localhost/static/public.txt');
        expect(publicFile.status).toBe(200);
        expect(await publicFile.text()).toBe('public fixture');
        for (const path of ['/static/admin/secret.txt', '/static/%61dmin/secret.txt']) {
          expect((await app.request(`http://localhost${path}`)).status).toBe(401);
        }
        // Upstream advisory regression: routing sees a different path from a
        // second decode. Neither static implementation may disclose the file.
        const bypass = await app.request('http://localhost/static/%%36%31dmin/secret.txt');
        expect(bypass.status).toBe(404);
        expect(await bypass.text()).not.toContain('private fixture');
        expect((await app.request('http://localhost/static/public.txt', { method: 'POST' })).status).toBe(404);
      } finally {
        await rm(root, { recursive: true, force: true });
      }
    },
  );

  it('normalizes encoded host letters consistently', () => {
    expect(uri.parse('//%41.com').host).toBe('a.com');
    expect(uri.equal('//%41.com', '//a.com')).toBe(true);
  });

  it('rejects an authority that a second URL parser would silently rewrite', () => {
    expect(uri.parse('http://a@b@evil.example/').error).toBeTruthy();
  });

  it('does not turn an encoded scheme into an executable URI', () => {
    expect(uri.parse('%6Aavascript:alert(1)').scheme).not.toBe('javascript');
    expect(uri.normalize('%6Aavascript:alert(1)')).not.toMatch(/^javascript:/i);
  });

  it('escapes the colon when serializing a suffix reference', () => {
    for (const scheme of ['javascript', 'data', 'vbscript']) {
      // Suffix output omits the input scheme, so the first emitted segment
      // must remain a relative path even when the component had a scheme.
      const suffix = uri.serialize({ scheme: 'https', path: `${scheme}:payload` }, { reference: 'suffix' });
      expect(suffix).toBe(`${scheme}%3Apayload`);
      expect(uri.parse(suffix).scheme).toBeUndefined();
    }
    // Suffix parsing treats a string as an authority. Invalid authority input
    // is rejected; normalize is not an HTML/URL sanitizer for invalid input.
    expect(uri.parse('javascript:alert(1)', { reference: 'suffix' }).error).toBeTruthy();
  });

  it('preserves the resource reached by normalized relative references', () => {
    for (const reference of ['../x', 'a/../b']) {
      const base = 'https://example.invalid/dir/page';
      expect(uri.resolve(base, uri.normalize(reference))).toBe(uri.resolve(base, reference));
    }
  });

  it('accepts nested SDK object schemas with strict keyword types', () => {
    expectTypeOf<false>().not.toMatchTypeOf<JsonSchemaType>();
    expectTypeOf<{ type: number }>().not.toMatchTypeOf<JsonSchemaType>();
    const schema: JsonSchemaType = {
      type: 'object',
      properties: {
        payload: { anyOf: [{ type: 'null' }, { type: 'array', items: { type: 'integer' } }] },
        mode: { enum: ['read', 'write'] },
      },
      required: ['payload', 'mode'],
      additionalProperties: false,
    };
    const { AjvJsonSchemaValidator } = fromSdk('@modelcontextprotocol/sdk/validation/ajv') as
      typeof import('@modelcontextprotocol/sdk/validation/ajv');
    const validate = new AjvJsonSchemaValidator().getValidator(schema);
    for (const payload of [null, [], [1, 2]]) {
      expect(validate({ payload, mode: 'read' }).valid).toBe(true);
    }
    for (const invalid of [
      { payload: ['1'], mode: 'read' },
      { payload: [1], mode: 'unknown' },
      { mode: 'read' },
      { payload: null, mode: 'read', unexpected: true },
    ]) {
      expect(validate(invalid).valid).toBe(false);
    }
  });

  it('validates MCP tool schemas and local references using the installed AJV consumer', () => {
    const { AjvJsonSchemaValidator } = fromSdk('@modelcontextprotocol/sdk/validation/ajv') as
      typeof import('@modelcontextprotocol/sdk/validation/ajv');
    const validate = new AjvJsonSchemaValidator().getValidator({
      $id: 'https://example.invalid/schemas/tool.json',
      $defs: { name: { type: 'string', minLength: 1 } },
      type: 'object', properties: { name: { $ref: '#/$defs/name' } },
      required: ['name'], additionalProperties: false,
    });
    expect(validate({ name: 'example' }).valid).toBe(true);
    expect(validate({ name: 7 }).valid).toBe(false);
    expect(validate({ name: '' }).valid).toBe(false);
  });

  it('bounds malformed IPv6 rejection while retaining the rate-limit consumer behavior', () => {
    const fromLimiter = createRequire(fromSdk.resolve('express-rate-limit'));
    const result = spawnSync(process.execPath, ['-e', `
      const { Address6 } = require(${JSON.stringify(fromLimiter.resolve('ip-address'))});
      const { ipKeyGenerator } = require(${JSON.stringify(fromSdk.resolve('express-rate-limit'))});
      console.log(JSON.stringify({
        valid: Address6.isValid('2001:db8::1'),
        key: ipKeyGenerator('2001:db8::1'),
        malformed: Address6.isValid('%'.repeat(256 * 1024) + '\\n'),
      }));
    `], { encoding: 'utf8', timeout: 2000 });
    // Isolate the advisory's long input in a bounded process: the vulnerable
    // synchronous regexp takes tens of seconds and must not stall the suite.
    expect(result.error).toBeUndefined();
    expect(result.status).toBe(0);
    expect(JSON.parse(result.stdout)).toEqual({ valid: true, key: '2001:db8::/56', malformed: false });
  });

  it('completes a real MCP initialize and tool-call roundtrip through the Node adapter', async () => {
    const { McpServer } = fromSdk('@modelcontextprotocol/sdk/server/mcp.js') as
      typeof import('@modelcontextprotocol/sdk/server/mcp.js');
    const { StreamableHTTPServerTransport } = fromSdk('@modelcontextprotocol/sdk/server/streamableHttp.js') as
      typeof import('@modelcontextprotocol/sdk/server/streamableHttp.js');
    const { Client } = fromSdk('@modelcontextprotocol/sdk/client/index.js') as
      typeof import('@modelcontextprotocol/sdk/client/index.js');
    const { StreamableHTTPClientTransport } = fromSdk('@modelcontextprotocol/sdk/client/streamableHttp.js') as
      typeof import('@modelcontextprotocol/sdk/client/streamableHttp.js');
    const mcp = new McpServer({ name: 'eventrelay-local-security-test', version: '1.0.0' });
    mcp.registerTool('ping', { description: 'Local consumer compatibility probe' }, async () => ({
      content: [{ type: 'text', text: 'pong' }],
    }));
    const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: randomUUID, enableJsonResponse: true });
    const client = new Client({ name: 'local-probe', version: '1.0.0' });
    const server = createServer((request, response) => {
      void transport.handleRequest(request, response).catch(() => {
        response.writeHead(500).end();
      });
    });
    try {
      await mcp.connect(transport);
      await new Promise<void>((resolve, reject) => {
        server.once('error', reject);
        server.listen(0, '127.0.0.1', resolve);
      });
      const address = server.address();
      if (!address || typeof address === 'string') throw new Error('Missing local test port');
      await client.connect(new StreamableHTTPClientTransport(new URL(`http://127.0.0.1:${address.port}/mcp`)));
      expect((await client.listTools()).tools.map((tool) => tool.name)).toEqual(['ping']);
      expect((await client.callTool({ name: 'ping', arguments: {} })).content).toEqual([{ type: 'text', text: 'pong' }]);
    } finally {
      await client.close();
      await mcp.close();
      server.closeAllConnections();
      await new Promise<void>((resolve) => server.close(() => resolve()));
    }
  }, 10000);
});
