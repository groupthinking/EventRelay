import type { RetryConfig } from './types';
import { getLogger } from '@repo/logger';

const logger = getLogger({ name: 'retry' });

const defaultRetryConfig: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
  retryCondition: (error: Error) => {
    // Retry on network errors, timeouts, 5xx errors
    return /network|timeout|50[0-9]/.test(error.message.toLowerCase());
  },
};

export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  config: Partial<RetryConfig> = {}
): Promise<T> {
  const finalConfig: RetryConfig = { ...defaultRetryConfig, ...config };
  let lastError: Error;

  for (let attempt = 0; attempt <= finalConfig.maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      const shouldRetry = finalConfig.retryCondition
        ? finalConfig.retryCondition(lastError)
        : true;

      if (!shouldRetry || attempt >= finalConfig.maxRetries) {
        logger.error('Retry exhausted', {
          attempt,
          maxRetries: finalConfig.maxRetries,
          error: lastError.message,
        });
        throw lastError;
      }

      // Exponential backoff: baseDelay * 2^attempt
      const delay = Math.min(
        finalConfig.baseDelay * Math.pow(2, attempt),
        finalConfig.maxDelay
      );

      logger.warn('Retrying after error', {
        attempt: attempt + 1,
        maxRetries: finalConfig.maxRetries,
        delay,
        error: lastError.message,
      });

      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError!;
}

export async function retryWithCircuitBreaker<T>(
  fn: () => Promise<T>,
  endpoint: string,
  circuitBreaker: any,
  config: Partial<RetryConfig> = {}
): Promise<T> {
  if (circuitBreaker.isOpen(endpoint)) {
    throw new Error(`Circuit breaker is open for ${endpoint}`);
  }

  try {
    const result = await retryWithBackoff(fn, config);
    circuitBreaker.recordSuccess(endpoint);
    return result;
  } catch (error) {
    circuitBreaker.recordFailure(endpoint);
    throw error;
  }
}
