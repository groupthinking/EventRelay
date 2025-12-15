import { EventBus } from '../core/eventBus.js';
import { NormalizedMetric } from '../processing/normalizer.js';
export interface StorageMetricData {
    size: number;
    location: string;
    fileType: string;
    timestamp: number;
}
export declare class StorageMetrics {
    private eventBus;
    private metrics;
    constructor(eventBus: EventBus);
    collect(): Promise<NormalizedMetric[]>;
    trackDirectory(dirPath: string): Promise<void>;
    reset(): void;
}
