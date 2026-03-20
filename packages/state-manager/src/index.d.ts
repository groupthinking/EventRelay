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
export declare class StateManager {
    private config;
    private upstash?;
    private redis?;
    private ratelimit?;
    private keyPrefix;
    constructor(config: StateManagerConfig);
    initialize(): Promise<void>;
    private getKey;
    set<T>(key: string, value: T, ttlSeconds?: number): Promise<void>;
    get<T>(key: string): Promise<T | null>;
    delete(key: string): Promise<void>;
    saveWorkflowState(state: WorkflowState): Promise<void>;
    getWorkflowState(workflowId: string): Promise<WorkflowState | null>;
    updateWorkflowStep(workflowId: string, step: number, data: Record<string, unknown>): Promise<WorkflowState | null>;
    markWorkflowCompleted(workflowId: string): Promise<void>;
    markWorkflowFailed(workflowId: string, error: string): Promise<void>;
    checkRateLimit(identifier: string): Promise<{
        success: boolean;
        remaining: number;
    }>;
    acquireLock(lockKey: string, ttlSeconds?: number): Promise<boolean>;
    releaseLock(lockKey: string): Promise<void>;
    disconnect(): Promise<void>;
}
export default StateManager;
