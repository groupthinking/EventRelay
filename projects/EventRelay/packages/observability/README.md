# OpenTelemetry Observability

Production-ready observability with OpenTelemetry tracing and metrics.

**Based on EventRelay's proven Python implementation**

## Features

- **Distributed Tracing**: Track operations across services with OTLP
- **Metrics**: Counters and histograms for performance monitoring
- **Workflow Integration**: Built-in instrumentation for Workflow.dev
- **Zero Config**: Works with standard OTEL environment variables
- **Fallback Mode**: Gracefully degrades when OTEL unavailable

## Quick Start

### 1. Initialize Observability

```typescript
import { initObservability } from '@repo/observability';

// Initialize at app startup
const obs = initObservability({
  serviceName: 'my-service',
  otlpEndpoint: process.env.OTEL_EXPORTER_OTLP_ENDPOINT,
  enabled: true
});
```

### 2. Trace Operations

```typescript
import { getObservability } from '@repo/observability';

const obs = getObservability();

await obs.trace('data-processing', { user_id: '123' }, async () => {
  // Your operation here
  const data = await fetchData();
  return processData(data);
});
```

### 3. Record Metrics

```typescript
// Record a counter
obs.recordMetrics('api_requests_total', 1, {
  endpoint: '/api/users',
  method: 'GET'
});

// Record operation duration
obs.recordDuration('database_query', 125, {
  query: 'SELECT',
  table: 'users'
});
```

### 4. Instrument Workflows

```typescript
import { getWorkflowInstrumentation } from '@repo/observability';

const instrumentation = getWorkflowInstrumentation();

await instrumentation.traceWorkflow(
  'data-sync',
  'run-123',
  async () => {
    // Workflow execution
    return await runDataSyncWorkflow();
  }
);
```

## Environment Variables

```env
# OTLP endpoint (required)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Optional: Service name (can also be set in code)
OTEL_SERVICE_NAME=my-service
```

## Integration Examples

### With Workflow.dev

```typescript
import { Workflow } from '@vercel/workflow';
import { getWorkflowInstrumentation } from '@repo/observability';

const instrumentation = getWorkflowInstrumentation();

export const tracedWorkflow = new Workflow('my-workflow')
  .step('step-1', async (context) => {
    return await instrumentation.traceStep(
      'my-workflow',
      'step-1',
      { input: context.input },
      async () => {
        // Step implementation
        return { result: 'data' };
      }
    );
  });
```

### With MCP Connectors

```typescript
import { PostgresConnector } from '@repo/mcp-connectors/postgres';
import { getObservability } from '@repo/observability';

const obs = getObservability();
const postgres = new PostgresConnector({ connectionString: '...' });

await obs.trace('postgres-query', { table: 'users' }, async () => {
  return await postgres.executeTool('query', {
    query: 'SELECT * FROM users'
  });
});
```

## Architecture

Based on EventRelay's `agents/observability_setup.py`:
- **Tracing**: OTLP trace exporter with gRPC
- **Metrics**: OTLP metric exporter with periodic export
- **Graceful Degradation**: Continues working without OTEL backend
- **Node.js SDK**: Official OpenTelemetry Node.js SDK

## Resources

- [OpenTelemetry Docs](https://opentelemetry.io/docs/)
- [Node.js SDK Guide](https://opentelemetry.io/docs/instrumentation/js/getting-started/nodejs/)
- [EventRelay Implementation](../../../agents/observability_setup.py)
