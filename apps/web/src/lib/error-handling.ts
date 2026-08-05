/**
 * Comprehensive error handling utilities for API routes
 */

/**
 * Circuit breaker for external API calls
 * Helps prevent cascading failures and implements exponential backoff
 */
export class CircuitBreaker {
  private failureCount = 0;
  private lastFailureTime = 0;
  private state: 'closed' | 'open' | 'half-open' = 'closed';

  constructor(
    private readonly failureThreshold = 5,
    private readonly resetTimeoutMs = 60_000
  ) {}

  async execute<T>(
    fn: () => Promise<T>,
    onStateChange?: (state: string) => void
  ): Promise<T> {
    if (this.state === 'open') {
      const timeSinceFailure = Date.now() - this.lastFailureTime;
      if (timeSinceFailure > this.resetTimeoutMs) {
        this.state = 'half-open';
        onStateChange?.('half-open');
      } else {
        throw new Error('CircuitBreaker is open - service temporarily unavailable');
      }
    }

    try {
      const result = await fn();
      if (this.state === 'half-open') {
        this.state = 'closed';
        this.failureCount = 0;
        onStateChange?.('closed');
      }
      return result;
    } catch (error) {
      this.failureCount++;
      this.lastFailureTime = Date.now();

      if (this.failureCount >= this.failureThreshold) {
        this.state = 'open';
        onStateChange?.('open');
      }
      throw error;
    }
  }

  getState() {
    return this.state;
  }
}

/**
 * Exponential backoff retry helper
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxAttempts = 3,
  baseDelayMs = 1000
): Promise<T> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      if (attempt < maxAttempts - 1) {
        const delayMs = baseDelayMs * Math.pow(2, attempt) + Math.random() * 1000;
        await new Promise(resolve => setTimeout(resolve, delayMs));
      }
    }
  }

  throw lastError || new Error('Max retry attempts exceeded');
}

/**
 * Timeout wrapper with custom error messages
 */
export function withTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number,
  timeoutMessage: string
): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error(timeoutMessage)), timeoutMs)
    ),
  ]);
}

/**
 * Safely parse JSON with detailed error info
 */
export async function parseJsonSafely(request: Request): Promise<Record<string, unknown>> {
  try {
    const text = await request.text();
    if (!text.trim()) {
      throw new Error('Request body is empty');
    }
    return JSON.parse(text) as Record<string, unknown>;
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new Error(`Invalid JSON: ${error.message}`);
    }
    throw error;
  }
}

/**
 * Validate required fields in request body
 */
export function validateRequiredFields(
  body: Record<string, unknown>,
  requiredFields: string[]
): void {
  const missing = requiredFields.filter(field => !body[field]);
  if (missing.length > 0) {
    throw new Error(`Missing required fields: ${missing.join(', ')}`);
  }
}

/**
 * Format API errors for consistent responses
 */
export function formatApiError(
  error: unknown,
  defaultMessage = 'An error occurred'
): { message: string; details?: string; code?: string } {
  if (error instanceof Error) {
    return {
      message: error.message || defaultMessage,
<<<<<<< HEAD
      details: error.stack?.split('\n')[1]?.trim(),
=======
      // Removed stack trace exposure for security
>>>>>>> origin/main
    };
  }

  if (typeof error === 'object' && error !== null) {
    const err = error as Record<string, unknown>;
    return {
      message: String(err.message || err.error || defaultMessage),
      code: String(err.code || ''),
    };
  }

  return {
    message: String(error) || defaultMessage,
  };
}
