import { createRequire } from 'node:module';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

// Use Node's installed-package resolution, including transitive dependencies.
// Mocking these imports would hide the hoisted API mismatch this guards against.
const fromWeb = createRequire(join(process.cwd(), 'package.json'));

describe('installed OpenTelemetry compatibility', () => {
  it('initializes instrumentation with the logging API it actually resolves', () => {
    const { InstrumentationBase } = fromWeb('@opentelemetry/instrumentation') as
      typeof import('@opentelemetry/instrumentation');
    class ProbeInstrumentation extends InstrumentationBase {
      protected init() { return []; }
    }

    const probe = new ProbeInstrumentation('eventrelay-compatibility-test', '1.0.0', {
      enabled: false,
    });
    expect(probe.isEnabled()).toBe(false);
    probe.disable();
  });

  it('records and exports a span through the maintained tracing SDK', async () => {
    const { TracerProvider, SimpleSpanProcessor, InMemorySpanExporter } =
      fromWeb('@opentelemetry/sdk-trace') as typeof import('@opentelemetry/sdk-trace');
    const { resourceFromAttributes } = fromWeb('@opentelemetry/resources') as
      typeof import('@opentelemetry/resources');
    const exporter = new InMemorySpanExporter();
    const provider = new TracerProvider({
      resource: resourceFromAttributes({ 'service.name': 'eventrelay-test' }),
      spanProcessors: [new SimpleSpanProcessor({ exporter })],
    });

    try {
      const span = provider.getTracer('compatibility-test').startSpan('video-processing');
      span.setAttribute('video.id', 'synthetic-video');
      span.end();
      await provider.forceFlush();

      const spans = exporter.getFinishedSpans();
      expect(spans).toHaveLength(1);
      expect(spans[0].name).toBe('video-processing');
      expect(spans[0].attributes['video.id']).toBe('synthetic-video');
      expect(spans[0].resource.attributes['service.name']).toBe('eventrelay-test');
    } finally {
      await provider.shutdown();
    }
  });

  it('shares the logging-capable API with the exporter and its SDK dependencies', () => {
    const api = fromWeb('@opentelemetry/api') as typeof import('@opentelemetry/api');
    expect(typeof api.logs.getLogger).toBe('function');
    const fromExporter = createRequire(fromWeb.resolve('@opentelemetry/exporter-trace-otlp-http'));
    const fromTransformer = createRequire(fromExporter.resolve('@opentelemetry/otlp-transformer'));

    for (const packageName of [
      '@opentelemetry/core',
      '@opentelemetry/resources',
      '@opentelemetry/sdk-trace',
      '@opentelemetry/sdk-logs',
      '@opentelemetry/sdk-metrics',
    ]) {
      const fromPackage = createRequire(fromTransformer.resolve(packageName));
      expect(fromPackage('@opentelemetry/api'), packageName).toBe(api);
    }
  });
});
