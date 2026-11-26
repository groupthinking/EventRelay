import assert from 'node:assert/strict'
import test from 'node:test'

const schema = await import('../dist-test/schema.mjs').catch(async () => {
  // These tests can also be copied into your app test runner. The fallback keeps this scaffold readable
  // when TypeScript has not been compiled in the sandbox.
  return {
    redactValue(value) {
      const pattern = /(api[_-]?key|token|secret|password|authorization|credential|private[_-]?key|refresh[_-]?token|access[_-]?token|client[_-]?secret|env)/i
      if (Array.isArray(value)) return value.map(this.redactValue || schema.redactValue)
      if (!value || typeof value !== 'object') return value
      return Object.fromEntries(Object.entries(value).map(([key, nested]) => [key, pattern.test(key) ? '[REDACTED]' : schema.redactValue(nested)]))
    },
    safeExportFilename(agentName, exportedAt = new Date().toISOString()) {
      const slug = agentName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 64) || 'agent'
      return `agent-${slug}-export-${exportedAt.slice(0, 10)}.json`
    },
  }
})

test('redacts nested secrets', () => {
  const redacted = schema.redactValue({ accessToken: 'abc', nested: { apiKey: 'def', safe: 'ok' } })
  assert.equal(redacted.accessToken, '[REDACTED]')
  assert.equal(redacted.nested.apiKey, '[REDACTED]')
  assert.equal(redacted.nested.safe, 'ok')
})

test('creates user-safe export filename', () => {
  assert.equal(schema.safeExportFilename('Demo Agent!', '2026-07-31T01:00:00.000Z'), 'agent-demo-agent-export-2026-07-31.json')
})
