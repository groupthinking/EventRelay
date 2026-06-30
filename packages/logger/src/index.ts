import pino from 'pino';
import { trace, context as otelContext } from '@opentelemetry/api';
import type { LoggerConfig, LogContext, StructuredLogger, LogLevel } from './types';

class Logger implements StructuredLogger {
  private logger: pino.Logger;

  constructor(config?: LoggerConfig) {
    const isDevelopment = process.env.NODE_ENV !== 'production';

    this.logger = pino({
      name: config?.name || 'app',
      level: config?.level || (isDevelopment ? 'debug' : 'info'),

      // Redact sensitive fields
      redact: {
        paths: config?.redact || [
          'password',
          'apiKey',
          'api_key',
          'token',
          'secret',
          'authorization',
          'cookie',
        ],
        censor: '[REDACTED]',
      },

      // Pretty printing in development
      transport: config?.pretty || isDevelopment
        ? {
            target: 'pino-pretty',
            options: {
              colorize: true,
              translateTime: 'HH:MM:ss.l',
              ignore: 'pid,hostname',
              singleLine: false,
            },
          }
        : undefined,

      // Base fields
      base: {
        env: process.env.NODE_ENV,
      },

      // Custom serializers
      serializers: {
        err: pino.stdSerializers.err,
        error: pino.stdSerializers.err,
      },

      // Timestamp
      timestamp: pino.stdTimeFunctions.isoTime,
    });
  }

  /**
   * Enrich log context with OpenTelemetry trace context
   */
  private enrichContext(context?: LogContext): LogContext {
    const enriched = { ...context };

    // Add OpenTelemetry trace context if available
    const span = trace.getSpan(otelContext.active());
    if (span) {
      const spanContext = span.spanContext();
      if (spanContext.traceId) {
        enriched.traceId = spanContext.traceId;
      }
      if (spanContext.spanId) {
        enriched.spanId = spanContext.spanId;
      }
    }

    return enriched;
  }

  trace(message: string, context?: LogContext): void {
    this.logger.trace(this.enrichContext(context), message);
  }

  debug(message: string, context?: LogContext): void {
    this.logger.debug(this.enrichContext(context), message);
  }

  info(message: string, context?: LogContext): void {
    this.logger.info(this.enrichContext(context), message);
  }

  warn(message: string, context?: LogContext): void {
    this.logger.warn(this.enrichContext(context), message);
  }

  error(message: string | Error, context?: LogContext): void {
    const enriched = this.enrichContext(context);

    if (message instanceof Error) {
      this.logger.error({ ...enriched, err: message }, message.message);
    } else {
      this.logger.error(enriched, message);
    }
  }

  fatal(message: string | Error, context?: LogContext): void {
    const enriched = this.enrichContext(context);

    if (message instanceof Error) {
      this.logger.fatal({ ...enriched, err: message }, message.message);
    } else {
      this.logger.fatal(enriched, message);
    }
  }

  /**
   * Create a child logger with additional context
   */
  child(context: LogContext): StructuredLogger {
    const childPino = this.logger.child(context);

    // Create new Logger instance wrapping the child pino logger
    const childLogger = new Logger();
    childLogger.logger = childPino;

    return childLogger;
  }
}

// Singleton logger instance
let defaultLogger: StructuredLogger | null = null;

/**
 * Get or create the default logger instance
 */
export function getLogger(config?: LoggerConfig): StructuredLogger {
  if (!defaultLogger) {
    defaultLogger = new Logger(config);
  }
  return defaultLogger;
}

/**
 * Create a new logger instance with custom configuration
 */
export function createLogger(config?: LoggerConfig): StructuredLogger {
  return new Logger(config);
}

// Export types
export type { LoggerConfig, LogContext, StructuredLogger, LogLevel } from './types';
