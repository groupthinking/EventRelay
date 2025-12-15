export type LogLevel = 'trace' | 'debug' | 'info' | 'warn' | 'error' | 'fatal';

export interface LoggerConfig {
  level?: LogLevel;
  name?: string;
  pretty?: boolean;
  redact?: string[];
  destination?: string;
}

export interface LogContext {
  requestId?: string;
  traceId?: string;
  spanId?: string;
  userId?: string;
  [key: string]: any;
}

export interface StructuredLogger {
  trace(message: string, context?: LogContext): void;
  debug(message: string, context?: LogContext): void;
  info(message: string, context?: LogContext): void;
  warn(message: string, context?: LogContext): void;
  error(message: string | Error, context?: LogContext): void;
  fatal(message: string | Error, context?: LogContext): void;
  child(context: LogContext): StructuredLogger;
}
