import { Redis as UpstashRedis } from '@upstash/redis';
import { Ratelimit } from '@upstash/ratelimit';
import Redis from 'ioredis';

export interface StateManagerConfig {
  provider: 'upstash' | 'redis';
  upstash?: {
    url: string;
    token: string;
  };
  redis?: {
    host: string;
    port: number;
    password?: string;
  };
  keyPrefix?: string;
}

export interface WorkflowState {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused';
  step: number;
  data: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
  error?: string;
}

export class StateManager {
  private config: StateManagerConfig;
  private upstash?: UpstashRedis;
  private redis?: Redis;
  private ratelimit?: Ratelimit;
  private keyPrefix: string;

  constructor(config: StateManagerConfig) {
    this.config = config;
    this.keyPrefix = config.keyPrefix || 'eventrelay:';
  }

  async initialize(): Promise<void> {
    if (this.config.provider === 'upstash' && this.config.upstash) {
      this.upstash = new UpstashRedis({
        url: this.config.upstash.url,
        token: this.config.upstash.token,
      });

      // Initialize rate limiter
      this.ratelimit = new Ratelimit({
        redis: this.upstash,
        limiter: Ratelimit.slidingWindow(100, '1 m'),
        analytics: true,
      });
    } else if (this.config.provider === 'redis' && this.config.redis) {
      this.redis = new Redis({
        host: this.config.redis.host,
        port: this.config.redis.port,
        password: this.config.redis.password,
      });
    }
  }

  private getKey(key: string): string {
    return `${this.keyPrefix}${key}`;
  }

  async set<T>(key: string, value: T, ttlSeconds?: number): Promise<void> {
    const serialized = JSON.stringify(value);
    const fullKey = this.getKey(key);

    if (this.config.provider === 'upstash' && this.upstash) {
      if (ttlSeconds) {
        await this.upstash.setex(fullKey, ttlSeconds, serialized);
      } else {
        await this.upstash.set(fullKey, serialized);
      }
    } else if (this.config.provider === 'redis' && this.redis) {
      if (ttlSeconds) {
        await this.redis.setex(fullKey, ttlSeconds, serialized);
      } else {
        await this.redis.set(fullKey, serialized);
      }
    }
  }

  async get<T>(key: string): Promise<T | null> {
    const fullKey = this.getKey(key);

    let value: string | null = null;
    if (this.config.provider === 'upstash' && this.upstash) {
      value = await this.upstash.get(fullKey);
    } else if (this.config.provider === 'redis' && this.redis) {
      value = await this.redis.get(fullKey);
    }

    return value ? JSON.parse(value) : null;
  }

  async delete(key: string): Promise<void> {
    const fullKey = this.getKey(key);

    if (this.config.provider === 'upstash' && this.upstash) {
      await this.upstash.del(fullKey);
    } else if (this.config.provider === 'redis' && this.redis) {
      await this.redis.del(fullKey);
    }
  }

  // Workflow state management
  async saveWorkflowState(state: WorkflowState): Promise<void> {
    const key = `workflow:${state.id}`;
    state.updatedAt = new Date().toISOString();
    await this.set(key, state, 86400 * 7); // 7 days TTL
  }

  async getWorkflowState(workflowId: string): Promise<WorkflowState | null> {
    return this.get<WorkflowState>(`workflow:${workflowId}`);
  }

  async updateWorkflowStep(
    workflowId: string,
    step: number,
    data: Record<string, unknown>
  ): Promise<WorkflowState | null> {
    const state = await this.getWorkflowState(workflowId);
    if (!state) return null;

    state.step = step;
    state.data = { ...state.data, ...data };
    await this.saveWorkflowState(state);
    return state;
  }

  async markWorkflowCompleted(workflowId: string): Promise<void> {
    const state = await this.getWorkflowState(workflowId);
    if (state) {
      state.status = 'completed';
      await this.saveWorkflowState(state);
    }
  }

  async markWorkflowFailed(workflowId: string, error: string): Promise<void> {
    const state = await this.getWorkflowState(workflowId);
    if (state) {
      state.status = 'failed';
      state.error = error;
      await this.saveWorkflowState(state);
    }
  }

  // Rate limiting
  async checkRateLimit(identifier: string): Promise<{ success: boolean; remaining: number }> {
    if (this.ratelimit) {
      const result = await this.ratelimit.limit(identifier);
      return { success: result.success, remaining: result.remaining };
    }
    return { success: true, remaining: -1 };
  }

  // Distributed locking
  async acquireLock(lockKey: string, ttlSeconds: number = 30): Promise<boolean> {
    const fullKey = this.getKey(`lock:${lockKey}`);
    const lockValue = Date.now().toString();

    if (this.config.provider === 'upstash' && this.upstash) {
      const result = await this.upstash.setnx(fullKey, lockValue);
      if (result === 1) {
        await this.upstash.expire(fullKey, ttlSeconds);
        return true;
      }
    } else if (this.config.provider === 'redis' && this.redis) {
      const result = await this.redis.setnx(fullKey, lockValue);
      if (result === 1) {
        await this.redis.expire(fullKey, ttlSeconds);
        return true;
      }
    }
    return false;
  }

  async releaseLock(lockKey: string): Promise<void> {
    await this.delete(`lock:${lockKey}`);
  }

  async disconnect(): Promise<void> {
    if (this.redis) {
      await this.redis.quit();
    }
  }
}

export default StateManager;
