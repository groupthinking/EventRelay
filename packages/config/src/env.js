"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.isTest = exports.isProduction = exports.isDevelopment = exports.env = void 0;
const zod_1 = require("zod");
const envSchema = zod_1.z.object({
    // Node Environment
    NODE_ENV: zod_1.z.enum(['development', 'production', 'test']).default('development'),
    // Supabase
    NEXT_PUBLIC_SUPABASE_URL: zod_1.z.string().url().optional(),
    NEXT_PUBLIC_SUPABASE_ANON_KEY: zod_1.z.string().optional(),
    SUPABASE_SERVICE_ROLE_KEY: zod_1.z.string().optional(),
    // Database
    DATABASE_URL: zod_1.z.string().optional(),
    DIRECT_URL: zod_1.z.string().optional(),
    // AI Providers
    XAI_API_KEY: zod_1.z.string().optional(),
    ANTHROPIC_API_KEY: zod_1.z.string().optional(),
    GOOGLE_GENERATIVE_AI_API_KEY: zod_1.z.string().optional(),
    OPENAI_API_KEY: zod_1.z.string().optional(),
    // Observability
    OTEL_EXPORTER_OTLP_ENDPOINT: zod_1.z.string().url().optional(),
    // App Configuration
    NEXT_PUBLIC_APP_URL: zod_1.z.string().url().optional(),
    NEXTAUTH_SECRET: zod_1.z.string().optional(),
    NEXTAUTH_URL: zod_1.z.string().url().optional(),
});
function validateEnv() {
    const parsed = envSchema.safeParse(process.env);
    if (!parsed.success) {
        console.error('❌ Invalid environment variables:');
        console.error(JSON.stringify(parsed.error.format(), null, 2));
        throw new Error('Invalid environment variables');
    }
    return parsed.data;
}
exports.env = validateEnv();
// Runtime environment checks
exports.isDevelopment = exports.env.NODE_ENV === 'development';
exports.isProduction = exports.env.NODE_ENV === 'production';
exports.isTest = exports.env.NODE_ENV === 'test';
//# sourceMappingURL=env.js.map