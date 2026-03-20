"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getLogger = getLogger;
exports.createLogger = createLogger;
const pino_1 = __importDefault(require("pino"));
const api_1 = require("@opentelemetry/api");
class Logger {
    logger;
    constructor(config) {
        const isDevelopment = process.env.NODE_ENV !== 'production';
        this.logger = (0, pino_1.default)({
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
                err: pino_1.default.stdSerializers.err,
                error: pino_1.default.stdSerializers.err,
            },
            // Timestamp
            timestamp: pino_1.default.stdTimeFunctions.isoTime,
        });
    }
    /**
     * Enrich log context with OpenTelemetry trace context
     */
    enrichContext(context) {
        const enriched = { ...context };
        // Add OpenTelemetry trace context if available
        const span = api_1.trace.getSpan(api_1.context.active());
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
    trace(message, context) {
        this.logger.trace(this.enrichContext(context), message);
    }
    debug(message, context) {
        this.logger.debug(this.enrichContext(context), message);
    }
    info(message, context) {
        this.logger.info(this.enrichContext(context), message);
    }
    warn(message, context) {
        this.logger.warn(this.enrichContext(context), message);
    }
    error(message, context) {
        const enriched = this.enrichContext(context);
        if (message instanceof Error) {
            this.logger.error({ ...enriched, err: message }, message.message);
        }
        else {
            this.logger.error(enriched, message);
        }
    }
    fatal(message, context) {
        const enriched = this.enrichContext(context);
        if (message instanceof Error) {
            this.logger.fatal({ ...enriched, err: message }, message.message);
        }
        else {
            this.logger.fatal(enriched, message);
        }
    }
    /**
     * Create a child logger with additional context
     */
    child(context) {
        const childPino = this.logger.child(context);
        // Create new Logger instance wrapping the child pino logger
        const childLogger = new Logger();
        childLogger.logger = childPino;
        return childLogger;
    }
}
// Singleton logger instance
let defaultLogger = null;
/**
 * Get or create the default logger instance
 */
function getLogger(config) {
    if (!defaultLogger) {
        defaultLogger = new Logger(config);
    }
    return defaultLogger;
}
/**
 * Create a new logger instance with custom configuration
 */
function createLogger(config) {
    return new Logger(config);
}
//# sourceMappingURL=index.js.map