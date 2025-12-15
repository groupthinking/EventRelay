# Durable Workflows with Workflow.dev

Production-ready durable workflows using [Vercel Workflow DevKit](https://useworkflow.dev/).

## What is Workflow.dev?

Workflow DevKit makes TypeScript functions durable, reliable, and observable:
- Functions pause for minutes/months and resume exactly where they stopped
- Survives deployments and crashes
- Automatic retry logic and persistence
- Zero infrastructure setup

## Available Workflows

### Data Processing Workflow
Multi-step data pipeline with automatic retry and persistence.

```typescript
import { runDataProcessing } from '@repo/workflows/data-processing';

const result = await runDataProcessing(
  'https://api.example.com/data',
  'https://api.example.com/storage'
);
```

### MCP Orchestration Workflow
Orchestrate MCP connectors (GitHub, Postgres, Slack) durably.

```typescript
import { runMCPOrchestration } from '@repo/workflows/mcp-orchestration';
import { GitHubConnector } from '@repo/mcp-connectors/github';
import { PostgresConnector } from '@repo/mcp-connectors/postgres';
import { SlackConnector } from '@repo/mcp-connectors/slack';

const result = await runMCPOrchestration({
  githubConnector: new GitHubConnector({ token, owner, repo }),
  postgresConnector: new PostgresConnector({ connectionString }),
  slackConnector: new SlackConnector({ token }),
  labels: ['bug', 'priority-high']
});
```

### Agent Monitoring Workflow
Periodic system health checks with alerting.

```typescript
import { runAgentMonitoring } from '@repo/workflows/mcp-orchestration';

const result = await runAgentMonitoring({
  postgresConnector,
  slackConnector
});
```

## Key Concepts

### Workflow Directive
Mark a function as durable:
```typescript
const myWorkflow = new Workflow('my-workflow')
```

### Step Directive
Mark units of work that auto-retry:
```typescript
.step('step-name', async (context) => {
  'use step';
  // This work is persisted and retries on failure
  return { result: 'data' };
})
```

## Features

- **Durability**: Workflows survive crashes and deployments
- **Retry Logic**: Steps automatically retry on failure
- **Observability**: Built-in monitoring and logging
- **MCP Integration**: Works seamlessly with @repo/mcp-connectors
- **Zero Config**: No queues, schedulers, or YAML needed

## Resources

- [Workflow.dev Documentation](https://useworkflow.dev/)
- [GitHub Repository](https://github.com/vercel/workflow)
- [Vercel Announcement](https://vercel.com/blog/introducing-workflow)
