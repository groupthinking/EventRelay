import type { LoggerConfig, StructuredLogger } from './types';
/**
 * Get or create the default logger instance
 */
export declare function getLogger(config?: LoggerConfig): StructuredLogger;
/**
 * Create a new logger instance with custom configuration
 */
export declare function createLogger(config?: LoggerConfig): StructuredLogger;
export type { LoggerConfig, LogContext, StructuredLogger, LogLevel } from './types';
