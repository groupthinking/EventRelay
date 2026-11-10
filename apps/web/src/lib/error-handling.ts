/**
 * Comprehensive error handling utilities for API routes
 */

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
 * Format API errors for consistent responses
 */
export function formatApiError(
  error: unknown,
  defaultMessage = 'An error occurred'
): { message: string; details?: string; code?: string } {
  if (error instanceof Error) {
    return {
      message: error.message || defaultMessage,
      // Removed stack trace exposure for security
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
