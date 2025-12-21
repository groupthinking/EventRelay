/**
 * ErrorReporter - Enterprise-grade error reporting and analytics service
 * Handles automatic error reporting, categorization, and monitoring integration
 */

export interface ErrorReport {
  errorId: string;
  error: {
    name: string;
    message: string;
    stack?: string;
  };
  errorInfo?: {
    componentStack?: string;
  };
  context: {
    level: string;
    userAgent: string;
    url: string;
    timestamp: string;
    userId: string;
    sessionId: string;
    [key: string]: any;
  };
  severity: 'low' | 'medium' | 'high' | 'critical';
  retryCount: number;
  tags?: string[];
}

export interface ErrorMetrics {
  errorRate: number;
  topErrors: Array<{ message: string; count: number }>;
  userImpact: number;
  meanTimeToRecovery: number;
}

export class ErrorReporter {
  private reportingEndpoint: string;
  private batchSize: number = 10;
  private batchTimeout: number = 30000; // 30 seconds
  private errorQueue: ErrorReport[] = [];
  private batchTimer?: NodeJS.Timeout;
  private retryAttempts: Map<string, number> = new Map();
  private maxRetryAttempts: number = 3;

  constructor() {
    this.reportingEndpoint = process.env.REACT_APP_ERROR_REPORTING_URL || '/api/errors/report';
    this.initializeBatchReporting();
  }

  /**
   * Report an error to the monitoring service
   */
  async reportError(report: ErrorReport): Promise<void> {
    try {
      // Add to batch queue
      this.errorQueue.push({
        ...report,
        tags: this.generateErrorTags(report)
      });

      // If queue is full, flush immediately
      if (this.errorQueue.length >= this.batchSize) {
        await this.flushErrorQueue();
      }

      // Update error metrics
      this.updateErrorMetrics(report);

      // Send critical errors immediately
      if (report.severity === 'critical') {
        await this.sendImmediateAlert(report);
      }

    } catch (error) {
      console.warn('Failed to queue error report:', error);
      // Store in localStorage as fallback
      this.storeErrorLocally(report);
    }
  }

  /**
   * Get current error metrics
   */
  getErrorMetrics(): ErrorMetrics {
    const storedMetrics = localStorage.getItem('errorMetrics');
    if (storedMetrics) {
      return JSON.parse(storedMetrics);
    }
    
    return {
      errorRate: 0,
      topErrors: [],
      userImpact: 0,
      meanTimeToRecovery: 0
    };
  }

  /**
   * Initialize batch reporting system
   */
  private initializeBatchReporting(): void {
    // Schedule periodic batch flush
    this.batchTimer = setInterval(() => {
      if (this.errorQueue.length > 0) {
        this.flushErrorQueue();
      }
    }, this.batchTimeout);

    // Flush queue on page unload
    window.addEventListener('beforeunload', () => {
      if (this.errorQueue.length > 0) {
        // Use sendBeacon for reliability during page unload
        const data = JSON.stringify({ errors: this.errorQueue });
        navigator.sendBeacon(this.reportingEndpoint, data);
      }
    });

    // Process any stored offline errors
    this.processOfflineErrors();
  }

  /**
   * Flush error queue to server
   */
  private async flushErrorQueue(): Promise<void> {
    if (this.errorQueue.length === 0) return;

    const errors = [...this.errorQueue];
    this.errorQueue = [];

    try {
      const response = await fetch(this.reportingEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          errors,
          batchId: `batch_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Clear retry attempts for successful reports
      errors.forEach(error => {
        this.retryAttempts.delete(error.errorId);
      });

    } catch (error) {
      console.warn('Failed to send error batch:', error);
      
      // Retry logic with exponential backoff
      errors.forEach(errorReport => {
        const attempts = this.retryAttempts.get(errorReport.errorId) || 0;
        if (attempts < this.maxRetryAttempts) {
          this.retryAttempts.set(errorReport.errorId, attempts + 1);
          
          // Re-queue with exponential backoff
          setTimeout(() => {
            this.errorQueue.push(errorReport);
          }, Math.pow(2, attempts) * 1000);
        } else {
          // Store permanently failed errors locally
          this.storeErrorLocally(errorReport);
        }
      });
    }
  }

  /**
   * Send immediate alert for critical errors
   */
  private async sendImmediateAlert(report: ErrorReport): Promise<void> {
    try {
      await fetch('/api/errors/alert', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...report,
          alertType: 'immediate',
          priority: 'high'
        }),
      });
    } catch (error) {
      console.warn('Failed to send immediate alert:', error);
    }
  }

  /**
   * Generate contextual tags for error categorization
   */
  private generateErrorTags(report: ErrorReport): string[] {
    const tags = [];

    // Component-based tags
    if (report.errorInfo?.componentStack) {
      const components = report.errorInfo.componentStack
        .match(/at (\w+)/g)
        ?.map(match => match.replace('at ', '').toLowerCase()) || [];
      tags.push(...components.slice(0, 3).map(comp => `component:${comp}`));
    }

    // Error type tags
    tags.push(`error-type:${report.error.name.toLowerCase()}`);

    // Severity tag
    tags.push(`severity:${report.severity}`);

    // Browser tags
    const ua = report.context.userAgent;
    if (ua.includes('Chrome')) tags.push('browser:chrome');
    else if (ua.includes('Firefox')) tags.push('browser:firefox');
    else if (ua.includes('Safari')) tags.push('browser:safari');

    // Page tags
    const path = new URL(report.context.url).pathname;
    tags.push(`page:${path.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase()}`);

    // Time-based tags
    const hour = new Date(report.context.timestamp).getHours();
    tags.push(`time-${hour < 6 ? 'night' : hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening'}`);

    return [...new Set(tags)]; // Remove duplicates
  }

  /**
   * Update error metrics in localStorage
   */
  private updateErrorMetrics(report: ErrorReport): void {
    const metrics = this.getErrorMetrics();
    
    // Update error rate (simplified)
    const now = Date.now();
    const errorRateKey = `errorRate_${Math.floor(now / 60000)}`; // Per minute
    const currentRate = parseInt(localStorage.getItem(errorRateKey) || '0');
    localStorage.setItem(errorRateKey, (currentRate + 1).toString());
    
    // Update top errors
    const errorKey = `${report.error.name}: ${report.error.message.substring(0, 50)}`;
    const topErrors = new Map(metrics.topErrors.map(e => [e.message, e.count]));
    topErrors.set(errorKey, (topErrors.get(errorKey) || 0) + 1);
    
    metrics.topErrors = Array.from(topErrors.entries())
      .map(([message, count]) => ({ message, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    localStorage.setItem('errorMetrics', JSON.stringify(metrics));
  }

  /**
   * Store error locally when network reporting fails
   */
  private storeErrorLocally(report: ErrorReport): void {
    try {
      const offlineErrors = JSON.parse(localStorage.getItem('offlineErrors') || '[]');
      offlineErrors.push({
        ...report,
        storedAt: new Date().toISOString()
      });
      
      // Keep only last 100 offline errors
      if (offlineErrors.length > 100) {
        offlineErrors.splice(0, offlineErrors.length - 100);
      }
      
      localStorage.setItem('offlineErrors', JSON.stringify(offlineErrors));
    } catch (error) {
      console.warn('Failed to store error locally:', error);
    }
  }

  /**
   * Process offline errors when connectivity is restored
   */
  private async processOfflineErrors(): Promise<void> {
    try {
      const offlineErrors = JSON.parse(localStorage.getItem('offlineErrors') || '[]');
      
      if (offlineErrors.length > 0) {
        // Add offline errors to queue for processing
        this.errorQueue.push(...offlineErrors);
        
        // Clear offline storage
        localStorage.removeItem('offlineErrors');
        
        // Flush queue
        await this.flushErrorQueue();
      }
    } catch (error) {
      console.warn('Failed to process offline errors:', error);
    }
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
    }
    
    // Final flush
    if (this.errorQueue.length > 0) {
      const data = JSON.stringify({ errors: this.errorQueue });
      navigator.sendBeacon(this.reportingEndpoint, data);
    }
  }
}

// Export singleton instance
export default new ErrorReporter();