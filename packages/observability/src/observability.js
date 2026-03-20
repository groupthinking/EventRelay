"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Observability = void 0;
exports.initObservability = initObservability;
exports.getObservability = getObservability;
const api_1 = require("@opentelemetry/api");
const sdk_node_1 = require("@opentelemetry/sdk-node");
const exporter_trace_otlp_grpc_1 = require("@opentelemetry/exporter-trace-otlp-grpc");
const resources_1 = require("@opentelemetry/resources");
const semantic_conventions_1 = require("@opentelemetry/semantic-conventions");
/**
 * OpenTelemetry observability system
 * Based on EventRelay's Python implementation
 */
class Observability {
    sdk = null;
    tracer = null;
    meter = null;
    enabled = false;
    serviceName;
    constructor(config) {
        this.serviceName = config.serviceName;
        const otlpEndpoint = config.otlpEndpoint || process.env.OTEL_EXPORTER_OTLP_ENDPOINT;
        if (config.enabled !== false && otlpEndpoint) {
            this.setupObservability(otlpEndpoint);
            this.enabled = true;
        }
        else {
            console.log('[Observability] Disabled (no OTLP endpoint configured)');
        }
    }
    setupObservability(endpoint) {
        // Configure resource with service name
        const resource = new resources_1.Resource({
            [semantic_conventions_1.SemanticResourceAttributes.SERVICE_NAME]: this.serviceName,
        });
        // Initialize SDK with OTLP exporters
        this.sdk = new sdk_node_1.NodeSDK({
            resource,
            traceExporter: new exporter_trace_otlp_grpc_1.OTLPTraceExporter({ url: endpoint }),
            // Note: metricReader configuration varies by OpenTelemetry version
            // Using traceExporter only for compatibility
        });
        // Start SDK
        this.sdk.start();
        // Get tracer and meter
        this.tracer = api_1.trace.getTracer(this.serviceName);
        this.meter = api_1.metrics.getMeter(this.serviceName);
        console.log(`[Observability] Initialized for ${this.serviceName} (endpoint: ${endpoint})`);
    }
    /**
     * Create a traced operation
     * @param operationName Name of the operation
     * @param attributes Optional attributes to add to the span
     * @param fn Function to trace
     */
    async trace(operationName, attributes = {}, fn) {
        if (!this.enabled || !this.tracer) {
            // Fallback: execute without tracing
            return await fn();
        }
        return await this.tracer.startActiveSpan(operationName, async (span) => {
            try {
                // Set attributes
                Object.entries(attributes).forEach(([key, value]) => {
                    span.setAttribute(key, value);
                });
                // Execute function
                const result = await fn();
                // Mark as successful
                span.setStatus({ code: api_1.SpanStatusCode.OK });
                return result;
            }
            catch (error) {
                // Record error
                span.setStatus({
                    code: api_1.SpanStatusCode.ERROR,
                    message: error.message || 'Unknown error'
                });
                span.recordException(error);
                throw error;
            }
            finally {
                span.end();
            }
        });
    }
    /**
     * Record metrics for an operation
     */
    recordMetrics(name, value, attributes = {}) {
        if (!this.enabled || !this.meter) {
            return;
        }
        const counter = this.meter.createCounter(name, {
            description: `Metric for ${name}`
        });
        counter.add(value, attributes);
    }
    /**
     * Record operation duration
     */
    recordDuration(operation, durationMs, attributes = {}) {
        if (!this.enabled || !this.meter) {
            return;
        }
        const histogram = this.meter.createHistogram(`${operation}_duration_ms`, {
            description: `Duration of ${operation} in milliseconds`
        });
        histogram.record(durationMs, attributes);
    }
    /**
     * Shutdown observability
     */
    async shutdown() {
        if (this.sdk) {
            await this.sdk.shutdown();
            console.log('[Observability] Shutdown complete');
        }
    }
}
exports.Observability = Observability;
/**
 * Singleton instance
 */
let observabilityInstance = null;
/**
 * Initialize observability (call once at app startup)
 */
function initObservability(config) {
    if (!observabilityInstance) {
        observabilityInstance = new Observability(config);
    }
    return observabilityInstance;
}
/**
 * Get observability instance
 */
function getObservability() {
    if (!observabilityInstance) {
        throw new Error('Observability not initialized. Call initObservability() first.');
    }
    return observabilityInstance;
}
//# sourceMappingURL=observability.js.map