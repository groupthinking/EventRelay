import { EventBus } from '../core/eventBus.js';
import { NormalizedMetric } from '../processing/normalizer.js';

export interface MemoryPathData {
  path: string;
  accessCount: number;
  lastAccess: number;
  firstAccess: number;
  operations: string[];
}

export class MemoryPathMetrics {
  private eventBus: EventBus;
  private pathData: Map<string, MemoryPathData>;

  constructor(eventBus: EventBus) {
    this.eventBus = eventBus;
    this.pathData = new Map();
  }

  async collect(): Promise<NormalizedMetric[]> {
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

  trackAccess(path: string, operation: string): void {
    const now = Date.now();
    const existing = this.pathData.get(path);

    if (existing) {
      existing.accessCount++;
      existing.lastAccess = now;
      existing.operations.push(operation);
    } else {
      const newData: MemoryPathData = {
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

  getTopPaths(limit: number = 10): MemoryPathData[] {
    return Array.from(this.pathData.values())
      .sort((a, b) => b.accessCount - a.accessCount)
      .slice(0, limit);
  }

  getPathHistory(path: string): MemoryPathData | undefined {
    return this.pathData.get(path);
  }

  getRecentAccesses(minutes: number = 60): MemoryPathData[] {
    const cutoff = Date.now() - (minutes * 60 * 1000);
    return Array.from(this.pathData.values())
      .filter(data => data.lastAccess >= cutoff);
  }

  reset(): void {
    this.pathData.clear();
  }

  analyzeAccessPatterns(): Record<string, any> {
    const totalAccesses = Array.from(this.pathData.values())
      .reduce((sum, data) => sum + data.accessCount, 0);

    const uniquePaths = this.pathData.size;

    const operationTypes = new Map<string, number>();
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
