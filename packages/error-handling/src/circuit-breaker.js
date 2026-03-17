"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.globalCircuitBreaker = exports.CircuitBreaker = void 0;
class CircuitBreaker {
    failures = new Map();
    lastFailure = new Map();
    threshold;
    timeout;
    constructor(config = { threshold: 5, timeout: 60000 }) {
        this.threshold = config.threshold;
        this.timeout = config.timeout;
    }
    isOpen(endpoint) {
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
    recordFailure(endpoint) {
        this.failures.set(endpoint, (this.failures.get(endpoint) || 0) + 1);
        this.lastFailure.set(endpoint, Date.now());
    }
    recordSuccess(endpoint) {
        this.failures.set(endpoint, 0);
    }
    reset(endpoint) {
        this.failures.delete(endpoint);
        this.lastFailure.delete(endpoint);
    }
}
exports.CircuitBreaker = CircuitBreaker;
// Global circuit breaker instance
exports.globalCircuitBreaker = new CircuitBreaker();
//# sourceMappingURL=circuit-breaker.js.map