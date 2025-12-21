/**
 * ErrorLogger - Structured error logging service with multiple output levels and formats
 * Provides comprehensive logging for development, staging, and production environments
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'fatal';

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  data?: any;
  error?: {
    name: string;
    message: string;
    stack?: string;
  };
  context?: {
    userId?: string;
    sessionId?: string;
    url?: string;
    userAgent?: string;
    [key: string]: any;
  };
  tags?: string[];
}

export interface LoggerConfig {
  level: LogLevel;
  enableConsole: boolean;
  enableLocalStorage: boolean;
  enableRemote: boolean;
  maxLocalEntries: number;
  remoteEndpoint?: string;
}

export class ErrorLogger {
  private config: LoggerConfig;
  private logBuffer: LogEntry[] = [];
  private bufferFlushInterval: number = 30000; // 30 seconds
  private flushTimer?: NodeJS.Timeout;
  
  private readonly levelPriority: Record<LogLevel, number> = {
    debug: 0,
    info: 1,
    warn: 2,
    error: 3,
    fatal: 4
  };

  constructor(config?: Partial<LoggerConfig>) {
    this.config = {
      level: (process.env.NODE_ENV === 'development' ? 'debug' : 'info') as LogLevel,
      enableConsole: true,
      enableLocalStorage: true,
      enableRemote: process.env.NODE_ENV === 'production',
      maxLocalEntries: 1000,
      remoteEndpoint: process.env.REACT_APP_LOGGING_URL || '/api/logs',
      ...config
    };

    this.initializeLogger();
  }

  /**
   * Log an error with full context
   */
  logError(errorData: any): void {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level: 'error',
      message: errorData.error?.message || 'Unknown error occurred',
      error: errorData.error,
      context: errorData.context,
      data: errorData,
      tags: this.generateLogTags(errorData)
    };

    this.writeLog(entry);
  }

  /**
   * Log at debug level
   */
  debug(message: string, data?: any, context?: any): void {
    this.log('debug', message, data, context);
  }

  /**
   * Log at info level
   */
  info(message: string, data?: any, context?: any): void {
    this.log('info', message, data, context);
  }

  /**
   * Log at warn level
   */
  warn(message: string, data?: any, context?: any): void {
    this.log('warn', message, data, context);
  }

  /**
   * Log at error level
   */
  error(message: string, error?: Error, data?: any, context?: any): void {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level: 'error',
      message,
      error: error ? {
        name: error.name,
        message: error.message,
        stack: error.stack
      } : undefined,
      data,
      context: {
        url: window.location.href,
        userAgent: navigator.userAgent,
        ...context
      },
      tags: ['error']
    };

    this.writeLog(entry);
  }

  /**
   * Log at fatal level
   */
  fatal(message: string, error?: Error, data?: any, context?: any): void {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level: 'fatal',
      message,
      error: error ? {
        name: error.name,
        message: error.message,
        stack: error.stack
      } : undefined,
      data,
      context: {
        url: window.location.href,
        userAgent: navigator.userAgent,
        ...context
      },
      tags: ['fatal', 'critical']
    };

    this.writeLog(entry);
  }

  /**
   * Generic log method
   */
  private log(level: LogLevel, message: string, data?: any, context?: any): void {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      data,
      context: {
        url: window.location.href,
        userAgent: navigator.userAgent,
        ...context
      },
      tags: [level]
    };

    this.writeLog(entry);
  }

  /**
   * Write log entry to all configured outputs
   */
  private writeLog(entry: LogEntry): void {
    // Check if log level meets threshold
    if (this.levelPriority[entry.level] < this.levelPriority[this.config.level]) {
      return;
    }

    // Console logging
    if (this.config.enableConsole) {
      this.writeToConsole(entry);
    }

    // Local storage logging
    if (this.config.enableLocalStorage) {
      this.writeToLocalStorage(entry);
    }

    // Remote logging
    if (this.config.enableRemote) {
      this.writeToRemote(entry);
    }

    // Add to buffer for batch processing
    this.logBuffer.push(entry);
  }

  /**
   * Write to browser console with proper formatting
   */
  private writeToConsole(entry: LogEntry): void {
    const timestamp = new Date(entry.timestamp).toLocaleTimeString();
    const prefix = `[${timestamp}] [${entry.level.toUpperCase()}]`;
    
    const args: any[] = [
      `${prefix} ${entry.message}`,
    ];

    // Add data if present
    if (entry.data) {
      args.push('\nData:', entry.data);
    }

    // Add error if present
    if (entry.error) {
      args.push('\nError:', entry.error);
    }

    // Add context if present
    if (entry.context) {
      args.push('\nContext:', entry.context);
    }

    // Use appropriate console method
    switch (entry.level) {
      case 'debug':
        console.debug(...args);
        break;
      case 'info':
        console.info(...args);
        break;
      case 'warn':
        console.warn(...args);
        break;
      case 'error':
      case 'fatal':
        console.error(...args);
        break;
      default:
        console.log(...args);
    }
  }

  /**
   * Write to localStorage for persistence
   */
  private writeToLocalStorage(entry: LogEntry): void {
    try {
      const logs = this.getStoredLogs();
      logs.push(entry);

      // Limit stored entries
      if (logs.length > this.config.maxLocalEntries) {
        logs.splice(0, logs.length - this.config.maxLocalEntries);
      }

      localStorage.setItem('errorLogs', JSON.stringify(logs));
    } catch (error) {
      console.warn('Failed to write to localStorage:', error);
    }
  }

  /**
   * Add log entry to remote buffer
   */
  private writeToRemote(entry: LogEntry): void {
    // Remote logs will be sent in batches via flushLogs
  }

  /**
   * Get stored logs from localStorage
   */
  getStoredLogs(): LogEntry[] {
    try {
      const stored = localStorage.getItem('errorLogs');
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.warn('Failed to read stored logs:', error);
      return [];
    }
  }

  /**
   * Clear stored logs
   */
  clearStoredLogs(): void {
    localStorage.removeItem('errorLogs');
  }

  /**
   * Get logs filtered by level and time range
   */
  getLogs(
    level?: LogLevel, 
    startTime?: Date, 
    endTime?: Date
  ): LogEntry[] {
    const logs = this.getStoredLogs();
    
    return logs.filter(log => {
      // Level filter
      if (level && log.level !== level) {
        return false;
      }

      // Time range filter
      const logTime = new Date(log.timestamp);
      if (startTime && logTime < startTime) {
        return false;
      }
      if (endTime && logTime > endTime) {
        return false;
      }

      return true;
    });
  }

  /**
   * Initialize logger with periodic flushing
   */
  private initializeLogger(): void {
    // Set up periodic log buffer flushing
    this.flushTimer = setInterval(() => {
      this.flushLogs();
    }, this.bufferFlushInterval);

    // Flush on page unload
    window.addEventListener('beforeunload', () => {
      this.flushLogs(true);
    });

    // Initial info log
    this.info('ErrorLogger initialized', {
      config: this.config,
      environment: process.env.NODE_ENV
    });
  }

  /**
   * Flush log buffer to remote endpoint
   */
  private async flushLogs(force: boolean = false): Promise<void> {
    if (!this.config.enableRemote || this.logBuffer.length === 0) {
      return;
    }

    // Only send error+ level logs to remote in production
    const logsToSend = this.logBuffer.filter(log => 
      process.env.NODE_ENV === 'development' || 
      this.levelPriority[log.level] >= this.levelPriority.error
    );

    if (logsToSend.length === 0) {
      this.logBuffer = [];
      return;
    }

    try {
      const payload = {
        logs: logsToSend,
        batchId: `log_batch_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        source: 'frontend',
        environment: process.env.NODE_ENV
      };

      if (force && navigator.sendBeacon) {
        // Use sendBeacon for reliability during page unload
        navigator.sendBeacon(
          this.config.remoteEndpoint!,
          JSON.stringify(payload)
        );
      } else {
        const response = await fetch(this.config.remoteEndpoint!, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
      }

      // Clear buffer after successful send
      this.logBuffer = [];

    } catch (error) {
      console.warn('Failed to flush logs to remote:', error);
      
      // Keep logs in buffer for retry, but limit size
      if (this.logBuffer.length > 100) {
        this.logBuffer.splice(0, this.logBuffer.length - 100);
      }
    }
  }

  /**
   * Generate contextual tags for log entries
   */
  private generateLogTags(errorData: any): string[] {
    const tags = [];

    // Add error type tags
    if (errorData.error?.name) {
      tags.push(`error-type:${errorData.error.name.toLowerCase()}`);
    }

    // Add severity tag
    if (errorData.severity) {
      tags.push(`severity:${errorData.severity}`);
    }

    // Add browser tag
    const ua = navigator.userAgent;
    if (ua.includes('Chrome')) tags.push('browser:chrome');
    else if (ua.includes('Firefox')) tags.push('browser:firefox');
    else if (ua.includes('Safari')) tags.push('browser:safari');

    return tags;
  }

  /**
   * Clean up logger resources
   */
  destroy(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }
    
    // Final flush
    this.flushLogs(true);
  }
}

// Export singleton instance
export default new ErrorLogger();