export interface NormalizedMetric {
    source: string;
    type: string;
    timestamp: number;
    value: number | string;
    metadata?: Record<string, any>;
}
export interface RawMetric {
    source: string;
    data: any;
    timestamp?: number | string;
}
export declare class DataNormalizer {
    normalize(rawMetric: RawMetric): NormalizedMetric;
    private normalizeTimestamp;
    private extractMetricData;
}
