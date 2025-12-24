import { Tracer, Meter, trace, metrics, context, SpanStatusCode } from '@opentelemetry/api';
import { NodeSDK } from '@opentelemetry/sdk-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-grpc';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-grpc';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';

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
export class Observability {
  private sdk: NodeSDK | null = null;
  private tracer: Tracer | null = null;
  private meter: Meter | null = null;
  private enabled: boolean = false;
  private serviceName: string;

  constructor(config: ObservabilityConfig) {
    this.serviceName = config.serviceName;
    const otlpEndpoint = config.otlpEndpoint || process.env.OTEL_EXPORTER_OTLP_ENDPOINT;

    if (config.enabled !== false && otlpEndpoint) {
      this.setupObservability(otlpEndpoint);
      this.enabled = true;
    } else {
      console.log('[Observability] Disabled (no OTLP endpoint configured)');
    }
  }

  private setupObservability(endpoint: string): void {
    // Configure resource with service name
    const resource = new Resource({
      [SemanticResourceAttributes.SERVICE_NAME]: this.serviceName,
    });

    // Initialize SDK with OTLP exporters
    this.sdk = new NodeSDK({
      resource,
      traceExporter: new OTLPTraceExporter({ url: endpoint }),
      // Note: metricReader configuration varies by OpenTelemetry version
      // Using traceExporter only for compatibility
    });

    // Start SDK
    this.sdk.start();

    // Get tracer and meter
    this.tracer = trace.getTracer(this.serviceName);
    this.meter = metrics.getMeter(this.serviceName);

    console.log(`[Observability] Initialized for ${this.serviceName} (endpoint: ${endpoint})`);
  }

  /**
   * Create a traced operation
   * @param operationName Name of the operation
   * @param attributes Optional attributes to add to the span
   * @param fn Function to trace
   */
  async trace<T>(
    operationName: string,
    attributes: Record<string, string | number | boolean> = {},
    fn: () => Promise<T>
  ): Promise<T> {
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
        span.setStatus({ code: SpanStatusCode.OK });
        return result;
      } catch (error: any) {
        // Record error
        span.setStatus({
          code: SpanStatusCode.ERROR,
          message: error.message || 'Unknown error'
        });
        span.recordException(error);
        throw error;
      } finally {
        span.end();
      }
    });
  }

  /**
   * Record metrics for an operation
   */
  recordMetrics(name: string, value: number, attributes: Record<string, string | number> = {}): void {
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
  recordDuration(operation: string, durationMs: number, attributes: Record<string, string | number> = {}): void {
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
  async shutdown(): Promise<void> {
    if (this.sdk) {
      await this.sdk.shutdown();
      console.log('[Observability] Shutdown complete');
    }
  }
}

/**
 * Singleton instance
 */
let observabilityInstance: Observability | null = null;

/**
 * Initialize observability (call once at app startup)
 */
export function initObservability(config: ObservabilityConfig): Observability {
  if (!observabilityInstance) {
    observabilityInstance = new Observability(config);
  }
  return observabilityInstance;
}

/**
 * Get observability instance
 */
export function getObservability(): Observability {
  if (!observabilityInstance) {
    throw new Error('Observability not initialized. Call initObservability() first.');
  }
  return observabilityInstance;
}
