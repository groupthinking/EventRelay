"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.StateManager = void 0;
const redis_1 = require("@upstash/redis");
const ratelimit_1 = require("@upstash/ratelimit");
const ioredis_1 = __importDefault(require("ioredis"));
class StateManager {
    config;
    upstash;
    redis;
    ratelimit;
    keyPrefix;
    constructor(config) {
        this.config = config;
        this.keyPrefix = config.keyPrefix || 'eventrelay:';
    }
    async initialize() {
        if (this.config.provider === 'upstash' && this.config.upstash) {
            this.upstash = new redis_1.Redis({
                url: this.config.upstash.url,
                token: this.config.upstash.token,
            });
            // Initialize rate limiter
            this.ratelimit = new ratelimit_1.Ratelimit({
                redis: this.upstash,
                limiter: ratelimit_1.Ratelimit.slidingWindow(100, '1 m'),
                analytics: true,
            });
        }
        else if (this.config.provider === 'redis' && this.config.redis) {
            this.redis = new ioredis_1.default({
                host: this.config.redis.host,
                port: this.config.redis.port,
                password: this.config.redis.password,
            });
        }
    }
    getKey(key) {
        return `${this.keyPrefix}${key}`;
    }
    async set(key, value, ttlSeconds) {
        const serialized = JSON.stringify(value);
        const fullKey = this.getKey(key);
        if (this.config.provider === 'upstash' && this.upstash) {
            if (ttlSeconds) {
                await this.upstash.setex(fullKey, ttlSeconds, serialized);
            }
            else {
                await this.upstash.set(fullKey, serialized);
            }
        }
        else if (this.config.provider === 'redis' && this.redis) {
            if (ttlSeconds) {
                await this.redis.setex(fullKey, ttlSeconds, serialized);
            }
            else {
                await this.redis.set(fullKey, serialized);
            }
        }
    }
    async get(key) {
        const fullKey = this.getKey(key);
        let value = null;
        if (this.config.provider === 'upstash' && this.upstash) {
            value = await this.upstash.get(fullKey);
        }
        else if (this.config.provider === 'redis' && this.redis) {
            value = await this.redis.get(fullKey);
        }
        return value ? JSON.parse(value) : null;
    }
    async delete(key) {
        const fullKey = this.getKey(key);
        if (this.config.provider === 'upstash' && this.upstash) {
            await this.upstash.del(fullKey);
        }
        else if (this.config.provider === 'redis' && this.redis) {
            await this.redis.del(fullKey);
        }
    }
    // Workflow state management
    async saveWorkflowState(state) {
        const key = `workflow:${state.id}`;
        state.updatedAt = new Date().toISOString();
        await this.set(key, state, 86400 * 7); // 7 days TTL
    }
    async getWorkflowState(workflowId) {
        return this.get(`workflow:${workflowId}`);
    }
    async updateWorkflowStep(workflowId, step, data) {
        const state = await this.getWorkflowState(workflowId);
        if (!state)
            return null;
        state.step = step;
        state.data = { ...state.data, ...data };
        await this.saveWorkflowState(state);
        return state;
    }
    async markWorkflowCompleted(workflowId) {
        const state = await this.getWorkflowState(workflowId);
        if (state) {
            state.status = 'completed';
            await this.saveWorkflowState(state);
        }
    }
    async markWorkflowFailed(workflowId, error) {
        const state = await this.getWorkflowState(workflowId);
        if (state) {
            state.status = 'failed';
            state.error = error;
            await this.saveWorkflowState(state);
        }
    }
    // Rate limiting
    async checkRateLimit(identifier) {
        if (this.ratelimit) {
            const result = await this.ratelimit.limit(identifier);
            return { success: result.success, remaining: result.remaining };
        }
        return { success: true, remaining: -1 };
    }
    // Distributed locking
    async acquireLock(lockKey, ttlSeconds = 30) {
        const fullKey = this.getKey(`lock:${lockKey}`);
        const lockValue = Date.now().toString();
        if (this.config.provider === 'upstash' && this.upstash) {
            const result = await this.upstash.setnx(fullKey, lockValue);
            if (result === 1) {
                await this.upstash.expire(fullKey, ttlSeconds);
                return true;
            }
        }
        else if (this.config.provider === 'redis' && this.redis) {
            const result = await this.redis.setnx(fullKey, lockValue);
            if (result === 1) {
                await this.redis.expire(fullKey, ttlSeconds);
                return true;
            }
        }
        return false;
    }
    async releaseLock(lockKey) {
        await this.delete(`lock:${lockKey}`);
    }
    async disconnect() {
        if (this.redis) {
            await this.redis.quit();
        }
    }
}
exports.StateManager = StateManager;
exports.default = StateManager;
//# sourceMappingURL=index.js.map