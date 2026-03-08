import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock the open telemetry modules
vi.mock('@opentelemetry/sdk-node', () => {
  return {
    NodeSDK: vi.fn().mockImplementation(() => ({
      start: vi.fn(),
      shutdown: vi.fn(),
    })),
  };
});

vi.mock('@opentelemetry/api', async () => {
  const actual = await vi.importActual('@opentelemetry/api');
  return {
    ...actual,
    trace: {
      getTracer: vi.fn().mockReturnValue({
        startActiveSpan: vi.fn((name, callback) => {
          const mockSpan = {
            setAttribute: vi.fn(),
            setStatus: vi.fn(),
            recordException: vi.fn(),
            end: vi.fn(),
          };
          return callback(mockSpan);
        }),
      }),
    },
    metrics: {
      getMeter: vi.fn().mockReturnValue({
        createCounter: vi.fn().mockReturnValue({ add: vi.fn() }),
        createHistogram: vi.fn().mockReturnValue({ record: vi.fn() }),
      }),
    },
  };
});

describe('observability module exports', () => {
  const testConfig = {
    serviceName: 'test-service',
    enabled: false // disabled to prevent actual connections
  };

  beforeEach(() => {
    // Reset vi modules so that each test gets a fresh internal observabilityInstance variable
    vi.resetModules();
    vi.clearAllMocks();
  });

  describe('initObservability', () => {
    it('should initialize and return an Observability instance', async () => {
      // Import freshly to get a new instance
      const mod = await import('./observability');
      const instance = mod.initObservability(testConfig);

      expect(instance).toBeInstanceOf(mod.Observability);
      // @ts-ignore - accessing private member for verification
      expect(instance.serviceName).toBe('test-service');
      // @ts-ignore - accessing private member for verification
      expect(instance.enabled).toBe(false);
    });

    it('should return the same instance when called multiple times', async () => {
      const mod = await import('./observability');
      const instance1 = mod.initObservability(testConfig);
      const instance2 = mod.initObservability({ serviceName: 'other-service' }); // Should ignore this config

      expect(instance1).toBe(instance2);
      // @ts-ignore
      expect(instance2.serviceName).toBe('test-service');
    });
  });

  describe('getObservability', () => {
    it('should throw an error if called before initialization', async () => {
      const mod = await import('./observability');
      expect(() => mod.getObservability()).toThrow('Observability not initialized. Call initObservability() first.');
    });

    it('should return the instance if already initialized', async () => {
      const mod = await import('./observability');
      const initialized = mod.initObservability(testConfig);
      const retrieved = mod.getObservability();

      expect(retrieved).toBe(initialized);
    });
  });
});
