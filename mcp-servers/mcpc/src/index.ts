#!/usr/bin/env node
/**
 * MCPC — Canonical MCP Orchestrator for EventRelay
 * ================================================
 *
 * Unified MCP server that consolidates functionality previously scattered
 * across 8 separate repositories:
 *   - MCPC (canonical, TypeScript)
 *   - MCP_ROUND_TABLE  → round_table tool
 *   - Mcpcserver       → server infrastructure
 *   - mcp-tools-extension → list_tools / execute_tool_chain
 *   - shared-state     → state_set / state_get / state_list / state_delete
 *
 * Transport: JSON-RPC 2.0 over stdio (MCP 2024-11-05 specification).
 *
 * Usage:
 *   node dist/index.js
 */

import * as readline from 'node:readline';
import { roundTableToolSchema } from './tools/round_table.js';
import { toolManagerSchemas } from './tools/tool_manager.js';
import { sharedStateSchemas } from './tools/shared_state.js';
import { dispatchTool } from './orchestrator.js';

const MCP_VERSION = '2024-11-05';
const SERVER_NAME = 'mcpc';
const SERVER_VERSION = '1.0.0';

/** All tools exposed by MCPC */
const ALL_TOOLS = [
  roundTableToolSchema,
  ...toolManagerSchemas,
  ...sharedStateSchemas,
];

// ── JSON-RPC helpers ──────────────────────────────────────────────────────────

function successResponse(id: unknown, result: unknown) {
  return { jsonrpc: '2.0', id, result };
}

function errorResponse(id: unknown, code: number, message: string) {
  return { jsonrpc: '2.0', id, error: { code, message } };
}

function send(obj: unknown) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

// ── Request handlers ──────────────────────────────────────────────────────────

function handleInitialize(id: unknown) {
  return successResponse(id, {
    serverInfo: { name: SERVER_NAME, version: SERVER_VERSION, mcpVersion: MCP_VERSION },
    capabilities: { tools: {} },
  });
}

function handleToolsList(id: unknown) {
  return successResponse(id, { tools: ALL_TOOLS });
}

async function handleToolsCall(id: unknown, params: Record<string, unknown>) {
  const toolName = params['name'] as string | undefined;
  const args = (params['arguments'] ?? {}) as Record<string, unknown>;

  if (!toolName) {
    return errorResponse(id, -32602, 'Missing required parameter: name');
  }

  const result = await dispatchTool(toolName, args);
  return successResponse(id, result);
}

// ── Main loop ─────────────────────────────────────────────────────────────────

async function main() {
  process.stderr.write(`[mcpc] MCPC MCP server starting (MCP ${MCP_VERSION})\n`);

  const rl = readline.createInterface({ input: process.stdin, terminal: false });

  for await (const line of rl) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    let request: Record<string, unknown>;
    try {
      request = JSON.parse(trimmed) as Record<string, unknown>;
    } catch {
      send(errorResponse(null, -32700, 'Parse error: invalid JSON'));
      continue;
    }

    const id = request['id'] ?? null;
    const method = request['method'] as string | undefined;
    const params = (request['params'] ?? {}) as Record<string, unknown>;

    try {
      let response: unknown;

      if (method === 'initialize') {
        response = handleInitialize(id);
      } else if (method === 'notifications/initialized') {
        // Notification — no response
        continue;
      } else if (method === 'tools/list') {
        response = handleToolsList(id);
      } else if (method === 'tools/call') {
        response = await handleToolsCall(id, params);
      } else {
        if (id !== null) {
          response = errorResponse(id, -32601, `Method not found: ${method}`);
        } else {
          continue; // Unknown notification — ignore
        }
      }

      send(response);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      process.stderr.write(`[mcpc] Unhandled error: ${msg}\n`);
      if (id !== null) {
        send(errorResponse(id, -32000, msg));
      }
    }
  }

  process.stderr.write('[mcpc] Server shutting down.\n');
}

main().catch((err) => {
  process.stderr.write(`[mcpc] Fatal: ${err}\n`);
  process.exit(1);
});
