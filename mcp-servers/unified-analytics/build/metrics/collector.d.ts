import { EventBus } from '../core/eventBus.js';
import { NormalizedMetric } from '../processing/normalizer.js';
export declare class MetricsCollector {
    private eventBus;
    private storageMetrics;
    private memoryPathMetrics;
    private collectedMetrics;
    constructor(eventBus: EventBus);
    private setupEventListeners;
    private storeMetric;
    collect(sources: string[], timeRange?: {
        start: string;
        end: string;
    }): Promise<Record<string, NormalizedMetric[]>>;
    private filterByTimeRange;
    analyze(metricTypes: string[]): Promise<Record<string, any>>;
    private analyzePerformance;
    private analyzeUsage;
    private analyzePatterns;
}
