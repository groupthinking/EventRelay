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

export class DataNormalizer {
  normalize(rawMetric: RawMetric): NormalizedMetric {
    const timestamp = this.normalizeTimestamp(rawMetric.timestamp);
    const { type, value, metadata } = this.extractMetricData(rawMetric.data);

    return {
      source: rawMetric.source,
      type,
      timestamp,
      value,
      ...(metadata && { metadata })
    };
  }

  private normalizeTimestamp(timestamp?: number | string): number {
    if (typeof timestamp === 'number') {
      return timestamp;
    }
    if (typeof timestamp === 'string') {
      return new Date(timestamp).getTime();
    }
    return Date.now();
  }

  private extractMetricData(data: any): { 
    type: string; 
    value: number | string;
    metadata?: Record<string, any>;
  } {
    // Handle memory path metrics
    if (data.path && data.accessCount) {
      return {
        type: 'path_access',
        value: data.accessCount,
        metadata: {
          path: data.path,
          lastAccess: data.lastAccess
        }
      };
    }

    // Handle storage metrics
    if (data.size !== undefined) {
      return {
        type: 'storage_usage',
        value: data.size,
        metadata: {
          location: data.location,
          type: data.fileType
        }
      };
    }

    // Handle performance metrics
    if (data.duration !== undefined) {
      return {
        type: 'performance',
        value: data.duration,
        metadata: {
          operation: data.operation,
          status: data.status
        }
      };
    }

    // Generic metrics
    return {
      type: 'generic',
      value: typeof data === 'object' ? JSON.stringify(data) : String(data)
    };
  }
}
