/**
 * Observability configuration
 */
export interface ObservabilityConfig {
    serviceName: string;
    otlpEndpoint?: string;
    enabled?: boolean;
}
/**
 * OpenTelemetry observability system
 * Based on EventRelay's Python implementation
 */
export declare class Observability {
    private sdk;
    private tracer;
    private meter;
    private enabled;
    private serviceName;
    constructor(config: ObservabilityConfig);
    private setupObservability;
    /**
     * Create a traced operation
     * @param operationName Name of the operation
     * @param attributes Optional attributes to add to the span
     * @param fn Function to trace
     */
    trace<T>(operationName: string, attributes: Record<string, string | number | boolean> | undefined, fn: () => Promise<T>): Promise<T>;
    /**
     * Record metrics for an operation
     */
    recordMetrics(name: string, value: number, attributes?: Record<string, string | number>): void;
    /**
     * Record operation duration
     */
    recordDuration(operation: string, durationMs: number, attributes?: Record<string, string | number>): void;
    /**
     * Shutdown observability
     */
    shutdown(): Promise<void>;
}
/**
 * Initialize observability (call once at app startup)
 */
export declare function initObservability(config: ObservabilityConfig): Observability;
/**
 * Get observability instance
 */
export declare function getObservability(): Observability;
