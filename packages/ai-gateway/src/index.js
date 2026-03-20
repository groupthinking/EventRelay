"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_FALLBACK_ORDER = exports.DEFAULT_MODELS = exports.ModelRegistry = exports.AIGateway = void 0;
const ai_1 = require("ai");
const models_1 = require("./models");
class AIGateway {
    registry;
    fallbackOrder;
    maxRetries;
    timeout;
    constructor(configs, options) {
        this.registry = new models_1.ModelRegistry(configs);
        this.fallbackOrder = options?.fallbackOrder || models_1.DEFAULT_FALLBACK_ORDER;
        this.maxRetries = options?.maxRetries || 3;
        this.timeout = options?.timeout || 30000;
    }
    /**
     * Generate text with automatic failover between providers
     */
    async generate(options) {
        const errors = [];
        for (const provider of this.fallbackOrder) {
            if (!this.registry.hasModel(provider)) {
                continue;
            }
            try {
                const model = this.registry.getModel(provider);
                if (!model)
                    continue;
                const result = await this.generateWithTimeout(model, provider, options);
                return result;
            }
            catch (error) {
                errors.push({
                    provider,
                    error: error instanceof Error ? error : new Error(String(error)),
                });
                console.warn(`[AIGateway] ${provider} failed, trying next provider...`, error);
            }
        }
        // All providers failed
        throw new Error(`All providers failed: ${errors.map((e) => `${e.provider}: ${e.error.message}`).join(', ')}`);
    }
    /**
     * Stream text with automatic failover
     */
    async stream(options) {
        const errors = [];
        for (const provider of this.fallbackOrder) {
            if (!this.registry.hasModel(provider)) {
                continue;
            }
            try {
                const model = this.registry.getModel(provider);
                if (!model)
                    continue;
                const { textStream } = await (0, ai_1.streamText)({
                    model,
                    prompt: options.prompt,
                    system: options.system,
                    maxTokens: options.maxTokens,
                    temperature: options.temperature,
                });
                return {
                    textStream,
                    provider,
                    model: model.modelId || 'unknown',
                };
            }
            catch (error) {
                errors.push({
                    provider,
                    error: error instanceof Error ? error : new Error(String(error)),
                });
                console.warn(`[AIGateway] ${provider} stream failed, trying next provider...`, error);
            }
        }
        throw new Error(`All providers failed for streaming: ${errors.map((e) => `${e.provider}: ${e.error.message}`).join(', ')}`);
    }
    /**
     * Generate with timeout enforcement
     */
    async generateWithTimeout(model, provider, options) {
        const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('Request timeout')), this.timeout));
        const generatePromise = (0, ai_1.generateText)({
            model,
            prompt: options.prompt,
            system: options.system,
            maxTokens: options.maxTokens,
            temperature: options.temperature,
        });
        const result = await Promise.race([generatePromise, timeoutPromise]);
        return {
            text: result.text,
            provider,
            model: model.modelId || 'unknown',
            usage: result.usage
                ? {
                    promptTokens: result.usage.promptTokens,
                    completionTokens: result.usage.completionTokens,
                    totalTokens: result.usage.totalTokens,
                }
                : undefined,
        };
    }
    /**
     * Get available providers
     */
    getAvailableProviders() {
        return this.registry.getAvailableProviders();
    }
    /**
     * Check if provider is available
     */
    hasProvider(provider) {
        return this.registry.hasModel(provider);
    }
}
exports.AIGateway = AIGateway;
// Export model utilities
var models_2 = require("./models");
Object.defineProperty(exports, "ModelRegistry", { enumerable: true, get: function () { return models_2.ModelRegistry; } });
Object.defineProperty(exports, "DEFAULT_MODELS", { enumerable: true, get: function () { return models_2.DEFAULT_MODELS; } });
Object.defineProperty(exports, "DEFAULT_FALLBACK_ORDER", { enumerable: true, get: function () { return models_2.DEFAULT_FALLBACK_ORDER; } });
//# sourceMappingURL=index.js.map