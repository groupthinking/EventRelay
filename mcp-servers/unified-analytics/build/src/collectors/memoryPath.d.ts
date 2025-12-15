import { EventBus } from '../core/eventBus.js';
import { NormalizedMetric } from '../processing/normalizer.js';
export interface MemoryPathData {
    path: string;
    accessCount: number;
    lastAccess: number;
    firstAccess: number;
    operations: string[];
}
export declare class MemoryPathMetrics {
    private eventBus;
    private pathData;
    constructor(eventBus: EventBus);
    collect(): Promise<NormalizedMetric[]>;
    trackAccess(path: string, operation: string): void;
    getTopPaths(limit?: number): MemoryPathData[];
    getPathHistory(path: string): MemoryPathData | undefined;
    getRecentAccesses(minutes?: number): MemoryPathData[];
    reset(): void;
    analyzeAccessPatterns(): Record<string, any>;
}
