import { describe, it, expect, vi, beforeEach } from 'vitest';
import { StateManager, WorkflowState } from './index';

// Hoist mocks properly to avoid ReferenceError
vi.mock('@upstash/redis', () => {
  const mockUpstash = {
    setex: vi.fn(),
    set: vi.fn(),
    get: vi.fn(),
    del: vi.fn(),
    setnx: vi.fn(),
    expire: vi.fn(),
  };
  return {
    Redis: class {
      constructor() {
        return mockUpstash;
      }
    },
    _mockUpstash: mockUpstash,
  };
});

vi.mock('ioredis', () => {
  const mockRedis = {
    setex: vi.fn(),
    set: vi.fn(),
    get: vi.fn(),
    del: vi.fn(),
    setnx: vi.fn(),
    expire: vi.fn(),
    quit: vi.fn(),
  };
  return {
    default: class {
      constructor() {
        return mockRedis;
      }
    },
    _mockRedis: mockRedis,
  };
});

vi.mock('@upstash/ratelimit', () => {
  const mockRatelimit = {
    limit: vi.fn().mockResolvedValue({ success: true, remaining: 99 }),
  };
  const RatelimitClass = class {
    constructor() {
      return mockRatelimit;
    }
  };
  // @ts-ignore
  RatelimitClass.slidingWindow = vi.fn();
  return { Ratelimit: RatelimitClass, _mockRatelimit: mockRatelimit };
});

import { _mockUpstash as mockUpstash } from '@upstash/redis';
import { _mockRedis as mockRedis } from 'ioredis';
import { _mockRatelimit as mockRatelimit } from '@upstash/ratelimit';

describe('StateManager', () => {
  let manager: StateManager;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Initialization', () => {
    it('initializes upstash provider correctly', async () => {
      manager = new StateManager({
        provider: 'upstash',
        upstash: { url: 'http://localhost', token: 'token' },
      });
      await manager.initialize();
      // Test that the provider methods work
      await manager.set('test', { foo: 'bar' });
      expect(mockUpstash.set).toHaveBeenCalled();
    });

    it('initializes redis provider correctly', async () => {
      manager = new StateManager({
        provider: 'redis',
        redis: { host: 'localhost', port: 6379 },
      });
      await manager.initialize();
      await manager.set('test', { foo: 'bar' });
      expect(mockRedis.set).toHaveBeenCalled();
    });
  });

  describe('CRUD operations - Upstash', () => {
    beforeEach(async () => {
      manager = new StateManager({
        provider: 'upstash',
        upstash: { url: 'http://localhost', token: 'token' },
      });
      await manager.initialize();
    });

    describe('set()', () => {
      it('calls set with prefix and serialized value', async () => {
        await manager.set('test-key', { foo: 'bar' });
        expect(mockUpstash.set).toHaveBeenCalledWith('eventrelay:test-key', JSON.stringify({ foo: 'bar' }));
      });

      it('calls setex when ttl is provided', async () => {
        await manager.set('test-key', { foo: 'bar' }, 60);
        expect(mockUpstash.setex).toHaveBeenCalledWith('eventrelay:test-key', 60, JSON.stringify({ foo: 'bar' }));
      });
    });

    describe('get()', () => {
      it('calls get with prefix and parses json', async () => {
        mockUpstash.get.mockResolvedValueOnce(JSON.stringify({ foo: 'bar' }));
        const result = await manager.get('test-key');
        expect(mockUpstash.get).toHaveBeenCalledWith('eventrelay:test-key');
        expect(result).toEqual({ foo: 'bar' });
      });

      it('returns null if value is not found', async () => {
        mockUpstash.get.mockResolvedValueOnce(null);
        const result = await manager.get('test-key');
        expect(mockUpstash.get).toHaveBeenCalledWith('eventrelay:test-key');
        expect(result).toBeNull();
      });
    });

    describe('delete()', () => {
      it('calls del with prefix', async () => {
        await manager.delete('test-key');
        expect(mockUpstash.del).toHaveBeenCalledWith('eventrelay:test-key');
      });
    });
  });

  describe('CRUD operations - Redis', () => {
    beforeEach(async () => {
      manager = new StateManager({
        provider: 'redis',
        redis: { host: 'localhost', port: 6379 },
      });
      await manager.initialize();
    });

    describe('set()', () => {
      it('calls set with prefix and serialized value', async () => {
        await manager.set('test-key', { foo: 'bar' });
        expect(mockRedis.set).toHaveBeenCalledWith('eventrelay:test-key', JSON.stringify({ foo: 'bar' }));
      });

      it('calls setex when ttl is provided', async () => {
        await manager.set('test-key', { foo: 'bar' }, 60);
        expect(mockRedis.setex).toHaveBeenCalledWith('eventrelay:test-key', 60, JSON.stringify({ foo: 'bar' }));
      });
    });

    describe('get()', () => {
      it('calls get with prefix and parses json', async () => {
        mockRedis.get.mockResolvedValueOnce(JSON.stringify({ foo: 'bar' }));
        const result = await manager.get('test-key');
        expect(mockRedis.get).toHaveBeenCalledWith('eventrelay:test-key');
        expect(result).toEqual({ foo: 'bar' });
      });

      it('returns null if value is not found', async () => {
        mockRedis.get.mockResolvedValueOnce(null);
        const result = await manager.get('test-key');
        expect(mockRedis.get).toHaveBeenCalledWith('eventrelay:test-key');
        expect(result).toBeNull();
      });
    });

    describe('delete()', () => {
      it('calls del with prefix', async () => {
        await manager.delete('test-key');
        expect(mockRedis.del).toHaveBeenCalledWith('eventrelay:test-key');
      });
    });
  });

  describe('Workflow operations', () => {
    let mockState: WorkflowState;

    beforeEach(async () => {
      manager = new StateManager({
        provider: 'upstash',
        upstash: { url: 'http://localhost', token: 'token' },
      });
      await manager.initialize();

      mockState = {
        id: '123',
        status: 'pending',
        step: 1,
        data: { test: 'data' },
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
    });

    describe('saveWorkflowState()', () => {
      it('saves state with 7 days TTL and updates updatedAt', async () => {
        // Freeze time
        const now = new Date('2023-01-01T00:00:00.000Z');
        vi.useFakeTimers();
        vi.setSystemTime(now);

        await manager.saveWorkflowState(mockState);

        expect(mockState.updatedAt).toBe(now.toISOString());
        expect(mockUpstash.setex).toHaveBeenCalledWith(
          'eventrelay:workflow:123',
          86400 * 7,
          JSON.stringify(mockState)
        );

        vi.useRealTimers();
      });
    });

    describe('getWorkflowState()', () => {
      it('gets state by workflow id', async () => {
        mockUpstash.get.mockResolvedValueOnce(JSON.stringify(mockState));
        const result = await manager.getWorkflowState('123');

        expect(mockUpstash.get).toHaveBeenCalledWith('eventrelay:workflow:123');
        expect(result).toEqual(mockState);
      });
    });

    describe('updateWorkflowStep()', () => {
      it('updates step and data when state exists', async () => {
        mockUpstash.get.mockResolvedValueOnce(JSON.stringify(mockState));

        const result = await manager.updateWorkflowStep('123', 2, { more: 'data' });

        expect(mockUpstash.get).toHaveBeenCalledWith('eventrelay:workflow:123');
        expect(result).toBeDefined();
        if (result) {
          expect(result.step).toBe(2);
          expect(result.data).toEqual({ test: 'data', more: 'data' });
          expect(mockUpstash.setex).toHaveBeenCalledWith(
            'eventrelay:workflow:123',
            86400 * 7,
            JSON.stringify(result)
          );
        }
      });

      it('returns null if state does not exist', async () => {
        mockUpstash.get.mockResolvedValueOnce(null);
        const result = await manager.updateWorkflowStep('123', 2, { more: 'data' });
        expect(result).toBeNull();
      });
    });

    describe('markWorkflowCompleted()', () => {
      it('updates status to completed', async () => {
        mockUpstash.get.mockResolvedValueOnce(JSON.stringify(mockState));
        await manager.markWorkflowCompleted('123');

        expect(mockUpstash.setex).toHaveBeenCalledWith(
          'eventrelay:workflow:123',
          86400 * 7,
          expect.stringContaining('"status":"completed"')
        );
      });
    });

    describe('markWorkflowFailed()', () => {
      it('updates status to failed and sets error', async () => {
        mockUpstash.get.mockResolvedValueOnce(JSON.stringify(mockState));
        await manager.markWorkflowFailed('123', 'test error');

        expect(mockUpstash.setex).toHaveBeenCalledWith(
          'eventrelay:workflow:123',
          86400 * 7,
          expect.stringMatching(/"status":"failed".*"error":"test error"/)
        );
      });
    });
  });

  describe('Other domain features', () => {
    beforeEach(async () => {
      manager = new StateManager({
        provider: 'upstash',
        upstash: { url: 'http://localhost', token: 'token' },
      });
      await manager.initialize();
    });

    describe('checkRateLimit()', () => {
      it('calls ratelimit.limit and returns success and remaining', async () => {
        const result = await manager.checkRateLimit('test-id');
        expect(mockRatelimit.limit).toHaveBeenCalledWith('test-id');
        expect(result).toEqual({ success: true, remaining: 99 });
      });

      it('returns true if ratelimit is not initialized', async () => {
        const redisManager = new StateManager({
          provider: 'redis',
          redis: { host: 'localhost', port: 6379 },
        });
        await redisManager.initialize();
        const result = await redisManager.checkRateLimit('test-id');
        expect(result).toEqual({ success: true, remaining: -1 });
      });
    });

    describe('acquireLock()', () => {
      it('returns true and sets expire if setnx succeeds (upstash)', async () => {
        mockUpstash.setnx.mockResolvedValueOnce(1);
        const result = await manager.acquireLock('my-lock', 60);

        expect(mockUpstash.setnx).toHaveBeenCalledWith(
          'eventrelay:lock:my-lock',
          expect.any(String)
        );
        expect(mockUpstash.expire).toHaveBeenCalledWith('eventrelay:lock:my-lock', 60);
        expect(result).toBe(true);
      });

      it('returns false if setnx fails (upstash)', async () => {
        mockUpstash.setnx.mockResolvedValueOnce(0);
        const result = await manager.acquireLock('my-lock', 60);

        expect(mockUpstash.setnx).toHaveBeenCalled();
        expect(mockUpstash.expire).not.toHaveBeenCalled();
        expect(result).toBe(false);
      });

      it('returns true and sets expire if setnx succeeds (redis)', async () => {
        const redisManager = new StateManager({
          provider: 'redis',
          redis: { host: 'localhost', port: 6379 },
        });
        await redisManager.initialize();

        mockRedis.setnx.mockResolvedValueOnce(1);
        const result = await redisManager.acquireLock('my-lock', 60);

        expect(mockRedis.setnx).toHaveBeenCalledWith(
          'eventrelay:lock:my-lock',
          expect.any(String)
        );
        expect(mockRedis.expire).toHaveBeenCalledWith('eventrelay:lock:my-lock', 60);
        expect(result).toBe(true);
      });
    });

    describe('releaseLock()', () => {
      it('deletes the lock key', async () => {
        await manager.releaseLock('my-lock');
        expect(mockUpstash.del).toHaveBeenCalledWith('eventrelay:lock:my-lock');
      });
    });

    describe('disconnect()', () => {
      it('calls quit on redis instance if it exists', async () => {
        const redisManager = new StateManager({
          provider: 'redis',
          redis: { host: 'localhost', port: 6379 },
        });
        await redisManager.initialize();
        await redisManager.disconnect();
        expect(mockRedis.quit).toHaveBeenCalled();
      });

      it('does nothing if redis instance does not exist', async () => {
        // For non-Redis providers, disconnect should be a no-op and resolve successfully
        await expect(manager.disconnect()).resolves.toBeUndefined();
      });
    });
  });
});
