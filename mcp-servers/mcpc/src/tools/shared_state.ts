/**
 * Shared State Tool
 *
 * Cross-agent shared state backed by an in-memory store.
 * Ports the shared-state continuity concept from the shared-state MCP server
 * into the unified MCPC orchestrator.
 */

export interface StateEntry {
  key: string;
  value: unknown;
  version: number;
  updated_at: string;
  author?: string;
}

/** In-memory state store */
const stateStore = new Map<string, StateEntry>();

/**
 * Write a value to shared state.
 */
export function setState(key: string, value: unknown, author?: string): StateEntry {
  if (!key || key.trim() === '') {
    throw new Error('key is required and must be non-empty');
  }
  const existing = stateStore.get(key);
  const entry: StateEntry = {
    key,
    value,
    version: (existing?.version ?? 0) + 1,
    updated_at: new Date().toISOString(),
    author,
  };
  stateStore.set(key, entry);
  return entry;
}

/**
 * Read a value from shared state.
 */
export function getState(key: string): StateEntry | undefined {
  return stateStore.get(key);
}

/**
 * Delete a key from shared state.
 */
export function deleteState(key: string): boolean {
  return stateStore.delete(key);
}

/**
 * List all keys currently in shared state.
 */
export function listStateKeys(): string[] {
  return [...stateStore.keys()];
}

/** MCP tool schema descriptors */
export const sharedStateSchemas = [
  {
    name: 'state_set',
    description: 'Write a value to the MCPC shared state store. Values persist for the lifetime of the server process.',
    inputSchema: {
      type: 'object',
      properties: {
        key: { type: 'string', description: 'State key' },
        value: { description: 'Value to store (any JSON-serialisable type)' },
        author: { type: 'string', description: 'Optional agent/user name performing the write' },
      },
      required: ['key', 'value'],
    },
  },
  {
    name: 'state_get',
    description: 'Read a value from the MCPC shared state store.',
    inputSchema: {
      type: 'object',
      properties: {
        key: { type: 'string', description: 'State key to read' },
      },
      required: ['key'],
    },
  },
  {
    name: 'state_list',
    description: 'List all keys currently stored in the MCPC shared state.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'state_delete',
    description: 'Delete a key from the MCPC shared state store.',
    inputSchema: {
      type: 'object',
      properties: {
        key: { type: 'string', description: 'State key to delete' },
      },
      required: ['key'],
    },
  },
] as const;
