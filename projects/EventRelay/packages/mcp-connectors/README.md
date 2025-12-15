# MCP Connectors

Production-ready Model Context Protocol (MCP) connectors for external services.

## Available Connectors

### Postgres Connector
Database operations with connection pooling and error handling.

```typescript
import { PostgresConnector } from '@repo/mcp-connectors/postgres';

const postgres = new PostgresConnector({
  connectionString: process.env.DATABASE_URL,
  maxConnections: 20
});

const result = await postgres.executeTool('query', {
  query: 'SELECT * FROM users WHERE id = $1',
  params: [userId]
});
```

### GitHub Connector
GitHub API integration with rate limit handling.

```typescript
import { GitHubConnector } from '@repo/mcp-connectors/github';

const github = new GitHubConnector({
  token: process.env.GITHUB_TOKEN,
  owner: 'your-org',
  repo: 'your-repo'
});

const issues = await github.executeTool('list_issues', {
  state: 'open',
  labels: ['bug']
});
```

### Slack Connector
Slack messaging and channel management.

```typescript
import { SlackConnector } from '@repo/mcp-connectors/slack';

const slack = new SlackConnector({
  token: process.env.SLACK_BOT_TOKEN
});

await slack.executeTool('send_message', {
  channel: '#general',
  text: 'Hello from MCP!'
});
```

## Features

- **Type Safety**: Full TypeScript support with type definitions
- **Error Handling**: Production-ready error handling and logging
- **Connection Management**: Automatic connection pooling and cleanup
- **MCP Protocol**: Follows Model Context Protocol standards

## Environment Variables

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/db
GITHUB_TOKEN=ghp_...
SLACK_BOT_TOKEN=xoxb-...
```
