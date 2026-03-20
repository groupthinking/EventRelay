"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.retryWithBackoff = retryWithBackoff;
exports.retryWithCircuitBreaker = retryWithCircuitBreaker;
const logger_1 = require("@repo/logger");
const logger = (0, logger_1.getLogger)({ name: 'retry' });
const defaultRetryConfig = {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 10000,
    retryCondition: (error) => {
        // Retry on network errors, timeouts, 5xx errors
        return /network|timeout|50[0-9]/.test(error.message.toLowerCase());
    },
};
async function retryWithBackoff(fn, config = {}) {
    const finalConfig = { ...defaultRetryConfig, ...config };
    let lastError;
    for (let attempt = 0; attempt <= finalConfig.maxRetries; attempt++) {
        try {
            return await fn();
        }
        catch (error) {
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
            const delay = Math.min(finalConfig.baseDelay * Math.pow(2, attempt), finalConfig.maxDelay);
            logger.warn('Retrying after error', {
                attempt: attempt + 1,
                maxRetries: finalConfig.maxRetries,
                delay,
                error: lastError.message,
            });
            await new Promise((resolve) => setTimeout(resolve, delay));
        }
    }
    throw lastError;
}
async function retryWithCircuitBreaker(fn, endpoint, circuitBreaker, config = {}) {
    if (circuitBreaker.isOpen(endpoint)) {
        throw new Error(`Circuit breaker is open for ${endpoint}`);
    }
    try {
        const result = await retryWithBackoff(fn, config);
        circuitBreaker.recordSuccess(endpoint);
        return result;
    }
    catch (error) {
        circuitBreaker.recordFailure(endpoint);
        throw error;
    }
}
//# sourceMappingURL=retry.js.map