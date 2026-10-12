import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generateUUID } from '../lib/utils.ts';
test('entity IDs remain valid and independent of insecure randomness', () => {
  const original = Math.random;
  Math.random = () => { throw new Error('Insecure randomness invoked'); };
  try {
    const ids = Array.from({ length: 1000 }, generateUUID);
    for (const id of ids) assert.match(id, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    assert.equal(new Set(ids).size, ids.length);
  } finally { Math.random = original; }
});
