import type { CircuitBreakerConfig } from './types';

export class CircuitBreaker {
  private failures = new Map<string, number>();
  private lastFailure = new Map<string, number>();
  private readonly threshold: number;
  private readonly timeout: number;

  constructor(config: CircuitBreakerConfig = { threshold: 5, timeout: 60000 }) {
    this.threshold = config.threshold;
    this.timeout = config.timeout;
  }

  isOpen(endpoint: string): boolean {
    const failures = this.failures.get(endpoint) || 0;
    const lastFailure = this.lastFailure.get(endpoint) || 0;

    if (failures >= this.threshold) {
      if (Date.now() - lastFailure > this.timeout) {
        // Reset circuit breaker
        this.failures.set(endpoint, 0);
        return false;
      }
      return true;
    }
    return false;
  }

  recordFailure(endpoint: string): void {
    this.failures.set(endpoint, (this.failures.get(endpoint) || 0) + 1);
    this.lastFailure.set(endpoint, Date.now());
  }

  recordSuccess(endpoint: string): void {
    this.failures.set(endpoint, 0);
  }

  reset(endpoint: string): void {
    this.failures.delete(endpoint);
    this.lastFailure.delete(endpoint);
  }
}

// Global circuit breaker instance
export const globalCircuitBreaker = new CircuitBreaker();
