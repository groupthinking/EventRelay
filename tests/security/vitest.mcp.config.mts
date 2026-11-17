import { defineConfig } from 'vitest/config';

// These regressions exercise the root GenAI -> MCP dependency graph. The web
// image intentionally installs only apps/web, so this suite has its own CI step.
export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/security/mcp-transitive-security.test.ts'],
  },
});
