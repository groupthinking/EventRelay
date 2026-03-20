import type { CircuitBreakerConfig } from './types';
export declare class CircuitBreaker {
    private failures;
    private lastFailure;
    private readonly threshold;
    private readonly timeout;
    constructor(config?: CircuitBreakerConfig);
    isOpen(endpoint: string): boolean;
    recordFailure(endpoint: string): void;
    recordSuccess(endpoint: string): void;
    reset(endpoint: string): void;
}
export declare const globalCircuitBreaker: CircuitBreaker;
