import * as fs from 'fs/promises';
import * as path from 'path';
export class StorageMetrics {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.metrics = [];
    }
    async collect() {
        return this.metrics.map(metric => ({
            source: 'storage',
            type: 'storage_usage',
            timestamp: metric.timestamp,
            value: metric.size,
            metadata: {
                location: metric.location,
                fileType: metric.fileType
            }
        }));
    }
    async trackDirectory(dirPath) {
        try {
            const files = await fs.readdir(dirPath, { withFileTypes: true });
            for (const file of files) {
                const fullPath = path.join(dirPath, file.name);
                if (file.isDirectory()) {
                    await this.trackDirectory(fullPath);
                }
                else {
                    const stats = await fs.stat(fullPath);
                    const metric = {
                        size: stats.size,
                        location: fullPath,
                        fileType: path.extname(file.name) || 'unknown',
                        timestamp: stats.mtimeMs
                    };
                    this.metrics.push(metric);
                    this.eventBus.emitMetric('storage', metric);
                }
            }
        }
        catch (error) {
            console.error(`Error tracking directory ${dirPath}:`, error);
        }
    }
    reset() {
        this.metrics = [];
    }
}
//# sourceMappingURL=storage.js.map