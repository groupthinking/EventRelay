import { StorageMetrics } from '../collectors/storage.js';
import { MemoryPathMetrics } from '../collectors/memoryPath.js';
export class MetricsCollector {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.storageMetrics = new StorageMetrics(eventBus);
        this.memoryPathMetrics = new MemoryPathMetrics(eventBus);
        this.collectedMetrics = new Map();
        this.setupEventListeners();
    }
    setupEventListeners() {
        this.eventBus.onMetric('storage', (metric) => {
            this.storeMetric('storage', metric);
        });
        this.eventBus.onMetric('memory-path', (metric) => {
            this.storeMetric('memory-path', metric);
        });
    }
    storeMetric(source, metric) {
        if (!this.collectedMetrics.has(source)) {
            this.collectedMetrics.set(source, []);
        }
        this.collectedMetrics.get(source)?.push(metric);
    }
    async collect(sources, timeRange) {
        const metrics = {};
        const startTime = timeRange ? new Date(timeRange.start).getTime() : undefined;
        const endTime = timeRange ? new Date(timeRange.end).getTime() : undefined;
        for (const source of sources) {
            if (source === 'all' || source === 'storage') {
                const storageData = await this.storageMetrics.collect();
                metrics.storage = this.filterByTimeRange(storageData, startTime, endTime);
            }
            if (source === 'all' || source === 'memory-path') {
                const memoryPathData = await this.memoryPathMetrics.collect();
                metrics['memory-path'] = this.filterByTimeRange(memoryPathData, startTime, endTime);
            }
        }
        return metrics;
    }
    filterByTimeRange(metrics, startTime, endTime) {
        if (!startTime && !endTime)
            return metrics;
        return metrics.filter(metric => {
            if (startTime && metric.timestamp < startTime)
                return false;
            if (endTime && metric.timestamp > endTime)
                return false;
            return true;
        });
    }
    async analyze(metricTypes) {
        const analysis = {};
        if (metricTypes.includes('all') || metricTypes.includes('performance')) {
            analysis.performance = this.analyzePerformance();
        }
        if (metricTypes.includes('all') || metricTypes.includes('usage')) {
            analysis.usage = this.analyzeUsage();
        }
        if (metricTypes.includes('all') || metricTypes.includes('patterns')) {
            analysis.patterns = this.analyzePatterns();
        }
        return analysis;
    }
    analyzePerformance() {
        const performanceMetrics = Array.from(this.collectedMetrics.values())
            .flat()
            .filter(m => m.type === 'performance');
        if (performanceMetrics.length === 0) {
            return { summary: 'No performance data available' };
        }
        const durations = performanceMetrics.map(m => Number(m.value));
        return {
            average: durations.reduce((a, b) => a + b, 0) / durations.length,
            min: Math.min(...durations),
            max: Math.max(...durations),
            totalOperations: performanceMetrics.length
        };
    }
    analyzeUsage() {
        const usageMetrics = Array.from(this.collectedMetrics.values())
            .flat()
            .filter(m => m.type === 'storage_usage' || m.type === 'path_access');
        if (usageMetrics.length === 0) {
            return { summary: 'No usage data available' };
        }
        const storageUsage = usageMetrics
            .filter(m => m.type === 'storage_usage')
            .reduce((total, m) => total + Number(m.value), 0);
        const pathAccesses = usageMetrics
            .filter(m => m.type === 'path_access')
            .reduce((acc, m) => {
            const path = m.metadata?.path;
            acc[path] = (acc[path] || 0) + Number(m.value);
            return acc;
        }, {});
        return {
            totalStorageUsage: storageUsage,
            pathAccessPatterns: pathAccesses,
            mostAccessedPaths: Object.entries(pathAccesses)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 5)
        };
    }
    analyzePatterns() {
        const allMetrics = Array.from(this.collectedMetrics.values()).flat();
        if (allMetrics.length === 0) {
            return { summary: 'No pattern data available' };
        }
        const patterns = allMetrics.reduce((acc, metric) => {
            const hour = new Date(metric.timestamp).getHours();
            acc[hour] = (acc[hour] || 0) + 1;
            return acc;
        }, {});
        const peakHour = Object.entries(patterns)
            .sort(([, a], [, b]) => b - a)[0];
        return {
            activityByHour: patterns,
            peakActivityHour: peakHour[0],
            peakActivityCount: peakHour[1]
        };
    }
}
//# sourceMappingURL=collector.js.map