# @repo/logger

High-performance structured logging with OpenTelemetry integration.

## Features

- ✅ **Structured JSON Logging**: Machine-readable logs for production
- ✅ **OpenTelemetry Integration**: Automatic trace/span correlation
- ✅ **High Performance**: Built on pino (one of the fastest Node.js loggers)
- ✅ **Pretty Development Mode**: Human-readable colored output
- ✅ **Sensitive Data Redaction**: Automatic removal of secrets
- ✅ **Child Loggers**: Contextual logging with inheritance
- ✅ **TypeScript Support**: Full type safety

## Installation

```bash
npm install @repo/logger
```

## Usage

### Basic Logging

```typescript
import { getLogger } from '@repo/logger';

const logger = getLogger();

logger.info('Application started');
logger.debug('Debug information', { userId: '123' });
logger.warn('Warning message', { metric: 'high_latency' });
logger.error('Error occurred', { error: new Error('Failed') });
```

### With Context

```typescript
const logger = getLogger();

logger.info('User logged in', {
  userId: '123',
  email: 'user@example.com',
  timestamp: new Date().toISOString(),
});
```

### Child Loggers

```typescript
const logger = getLogger();

// Create child logger with request context
const requestLogger = logger.child({
  requestId: 'req-123',
  path: '/api/users',
  method: 'GET',
});

requestLogger.info('Processing request');
requestLogger.debug('Query parameters', { limit: 10 });
requestLogger.info('Request completed', { duration: 45 });
```

### Error Logging

```typescript
const logger = getLogger();

try {
  throw new Error('Database connection failed');
} catch (error) {
  logger.error(error, {
    operation: 'db_connect',
    database: 'postgres',
  });
}
```

### Custom Configuration

```typescript
import { createLogger } from '@repo/logger';

const logger = createLogger({
  name: 'my-service',
  level: 'debug',
  pretty: true,
  redact: ['password', 'token', 'apiKey'],
});

logger.info('Custom logger initialized');
```

### Next.js API Route Integration

```typescript
// app/api/users/route.ts
import { getLogger } from '@repo/logger';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const logger = getLogger().child({
    requestId: crypto.randomUUID(),
    path: request.nextUrl.pathname,
  });

  logger.info('Fetching users');

  try {
    const users = await fetchUsers();
    logger.info('Users fetched successfully', { count: users.length });
    return NextResponse.json({ users });
  } catch (error) {
    logger.error(error, { operation: 'fetch_users' });
    return NextResponse.json(
      { error: 'Failed to fetch users' },
      { status: 500 }
    );
  }
}
```

### With OpenTelemetry

```typescript
import { getLogger } from '@repo/logger';
import { getObservability } from '@repo/observability';

const logger = getLogger();
const obs = getObservability();

await obs.trace('process-data', { dataId: '123' }, async () => {
  // Logs will automatically include traceId and spanId
  logger.info('Processing data');

  const result = await processData();

  logger.info('Data processed', { resultId: result.id });
  return result;
});
```

### With AI Gateway

```typescript
import { getLogger } from '@repo/logger';
import { AIGateway } from '@repo/ai-gateway';

const logger = getLogger();
const gateway = new AIGateway([...]);

logger.info('Generating AI response');

try {
  const result = await gateway.generate({
    prompt: 'Explain quantum computing',
  });

  logger.info('AI response generated', {
    provider: result.provider,
    tokens: result.usage?.totalTokens,
  });
} catch (error) {
  logger.error(error, { operation: 'ai_generate' });
}
```

### Middleware Pattern

```typescript
// middleware.ts
import { getLogger } from '@repo/logger';
import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  const requestId = crypto.randomUUID();
  const logger = getLogger().child({
    requestId,
    path: request.nextUrl.pathname,
    method: request.method,
  });

  logger.info('Request received');

  const response = NextResponse.next();
  response.headers.set('X-Request-ID', requestId);

  return response;
}
```

## API Reference

### `getLogger(config?: LoggerConfig): StructuredLogger`

Get or create the singleton logger instance.

### `createLogger(config?: LoggerConfig): StructuredLogger`

Create a new logger instance with custom configuration.

### `LoggerConfig`

```typescript
interface LoggerConfig {
  level?: 'trace' | 'debug' | 'info' | 'warn' | 'error' | 'fatal';
  name?: string;
  pretty?: boolean;
  redact?: string[];
  destination?: string;
}
```

### `StructuredLogger`

```typescript
interface StructuredLogger {
  trace(message: string, context?: LogContext): void;
  debug(message: string, context?: LogContext): void;
  info(message: string, context?: LogContext): void;
  warn(message: string, context?: LogContext): void;
  error(message: string | Error, context?: LogContext): void;
  fatal(message: string | Error, context?: LogContext): void;
  child(context: LogContext): StructuredLogger;
}
```

## Log Levels

- **trace**: Very detailed debugging (e.g., function entry/exit)
- **debug**: Detailed debugging information
- **info**: General informational messages
- **warn**: Warning messages (non-critical issues)
- **error**: Error messages (failures that need attention)
- **fatal**: Critical errors (application cannot continue)

## Automatic Redaction

The following fields are automatically redacted:
- `password`
- `apiKey` / `api_key`
- `token`
- `secret`
- `authorization`
- `cookie`

## OpenTelemetry Correlation

When used with `@repo/observability`, logs automatically include:
- `traceId`: Distributed trace identifier
- `spanId`: Current span identifier

This enables correlation between logs and traces in observability platforms.

## Environment Variables

```bash
NODE_ENV=production  # Controls default log level and pretty printing
LOG_LEVEL=debug      # Override default log level
```

## Production Best Practices

1. **Use appropriate log levels**
   - Don't log sensitive data at info level
   - Use debug for detailed troubleshooting
   - Reserve error for actual failures

2. **Add context to logs**
   - Include requestId, userId, traceId
   - Add operation-specific metadata
   - Use child loggers for scoped context

3. **Log structured data**
   - Use context objects instead of string interpolation
   - Enables querying and filtering in log aggregation tools

4. **Avoid logging in tight loops**
   - Log at appropriate granularity
   - Consider sampling for high-frequency events

## Related Packages

- `@repo/observability` - OpenTelemetry tracing and metrics
- `@repo/ai-gateway` - Multi-model AI with logging
- `@repo/workflows` - Durable workflows with logging

## Resources

- [Pino Docs](https://getpino.io/)
- [OpenTelemetry Logs](https://opentelemetry.io/docs/specs/otel/logs/)
- [Structured Logging Best Practices](https://www.thoughtworks.com/insights/blog/structured-logging)
