export class MemoryPathMetrics {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.pathData = new Map();
    }
    async collect() {
        return Array.from(this.pathData.values()).map(data => ({
            source: 'memory-path',
            type: 'path_access',
            timestamp: data.lastAccess,
            value: data.accessCount,
            metadata: {
                path: data.path,
                firstAccess: data.firstAccess,
                operations: data.operations
            }
        }));
    }
    trackAccess(path, operation) {
        const now = Date.now();
        const existing = this.pathData.get(path);
        if (existing) {
            existing.accessCount++;
            existing.lastAccess = now;
            existing.operations.push(operation);
        }
        else {
            const newData = {
                path,
                accessCount: 1,
                lastAccess: now,
                firstAccess: now,
                operations: [operation]
            };
            this.pathData.set(path, newData);
        }
        this.eventBus.emitMetric('memory-path', this.pathData.get(path));
    }
    getTopPaths(limit = 10) {
        return Array.from(this.pathData.values())
            .sort((a, b) => b.accessCount - a.accessCount)
            .slice(0, limit);
    }
    getPathHistory(path) {
        return this.pathData.get(path);
    }
    getRecentAccesses(minutes = 60) {
        const cutoff = Date.now() - (minutes * 60 * 1000);
        return Array.from(this.pathData.values())
            .filter(data => data.lastAccess >= cutoff);
    }
    reset() {
        this.pathData.clear();
    }
    analyzeAccessPatterns() {
        const totalAccesses = Array.from(this.pathData.values())
            .reduce((sum, data) => sum + data.accessCount, 0);
        const uniquePaths = this.pathData.size;
        const operationTypes = new Map();
        this.pathData.forEach(data => {
            data.operations.forEach(op => {
                operationTypes.set(op, (operationTypes.get(op) || 0) + 1);
            });
        });
        return {
            totalAccesses,
            uniquePaths,
            operationDistribution: Object.fromEntries(operationTypes),
            topPaths: this.getTopPaths(5),
            recentActivity: this.getRecentAccesses(15)
        };
    }
}
//# sourceMappingURL=memoryPath.js.map