import type { RetryConfig } from './types';
export declare function retryWithBackoff<T>(fn: () => Promise<T>, config?: Partial<RetryConfig>): Promise<T>;
export declare function retryWithCircuitBreaker<T>(fn: () => Promise<T>, endpoint: string, circuitBreaker: any, config?: Partial<RetryConfig>): Promise<T>;
