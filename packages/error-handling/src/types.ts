export interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  retryCondition?: (error: Error) => boolean;
}

export interface CircuitBreakerConfig {
  threshold: number;
  timeout: number;
}

export interface ErrorContext {
  errorId: string;
  timestamp: string;
  url?: string;
  userId?: string;
  [key: string]: any;
}
