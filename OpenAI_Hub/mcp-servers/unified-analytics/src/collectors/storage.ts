import { EventBus } from '../core/eventBus.js';
import { NormalizedMetric } from '../processing/normalizer.js';
import * as fs from 'fs/promises';
import * as path from 'path';

export interface StorageMetricData {
  size: number;
  location: string;
  fileType: string;
  timestamp: number;
}

export class StorageMetrics {
  private eventBus: EventBus;
  private metrics: StorageMetricData[];

  constructor(eventBus: EventBus) {
    this.eventBus = eventBus;
    this.metrics = [];
  }

  async collect(): Promise<NormalizedMetric[]> {
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

  async trackDirectory(dirPath: string): Promise<void> {
    try {
      const files = await fs.readdir(dirPath, { withFileTypes: true });
      
      for (const file of files) {
        const fullPath = path.join(dirPath, file.name);
        
        if (file.isDirectory()) {
          await this.trackDirectory(fullPath);
        } else {
          const stats = await fs.stat(fullPath);
          const metric: StorageMetricData = {
            size: stats.size,
            location: fullPath,
            fileType: path.extname(file.name) || 'unknown',
            timestamp: stats.mtimeMs
          };
          
          this.metrics.push(metric);
          this.eventBus.emitMetric('storage', metric);
        }
      }
    } catch (error) {
      console.error(`Error tracking directory ${dirPath}:`, error);
    }
  }

  reset(): void {
    this.metrics = [];
  }
}
