# @repo/error-handling

Production-grade error handling with boundaries, retry logic, and circuit breakers.

## Features

- ✅ **Error Boundaries**: React error boundaries with auto-recovery
- ✅ **Retry Logic**: Exponential backoff with configurable conditions
- ✅ **Circuit Breakers**: Prevent cascading failures
- ✅ **Structured Logging**: Integrated with @repo/logger
- ✅ **TypeScript**: Full type safety

## Usage

### Error Boundary

```typescript
import { ErrorBoundary } from '@repo/error-handling';

function App() {
  return (
    <ErrorBoundary fallback={<div>Custom error UI</div>}>
      <YourApp />
    </ErrorBoundary>
  );
}
```

### Retry with Backoff

```typescript
import { retryWithBackoff } from '@repo/error-handling';

const data = await retryWithBackoff(
  async () => fetch('/api/data').then(r => r.json()),
  {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 10000,
  }
);
```

### Circuit Breaker

```typescript
import { globalCircuitBreaker } from '@repo/error-handling';

if (globalCircuitBreaker.isOpen('/api/endpoint')) {
  // Serve fallback or cached data
  return getCachedData();
}

try {
  const result = await fetch('/api/endpoint');
  globalCircuitBreaker.recordSuccess('/api/endpoint');
  return result;
} catch (error) {
  globalCircuitBreaker.recordFailure('/api/endpoint');
  throw error;
}
```

## Based On

EventRelay production implementations:
- frontend/src/components/ErrorBoundary/GlobalErrorBoundary.tsx
- frontend/src/services/api.ts
