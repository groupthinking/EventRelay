"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_FALLBACK_ORDER = exports.DEFAULT_MODELS = exports.ModelRegistry = void 0;
const openai_1 = require("@ai-sdk/openai");
const anthropic_1 = require("@ai-sdk/anthropic");
const google_1 = require("@ai-sdk/google");
class ModelRegistry {
    models = new Map();
    constructor(configs) {
        for (const config of configs) {
            this.registerModel(config);
        }
    }
    registerModel(config) {
        let model;
        switch (config.provider) {
            case 'grok':
                // Grok uses OpenAI-compatible API
                model = (0, openai_1.openai)(config.model || 'grok-beta', {
                    baseURL: 'https://api.x.ai/v1',
                    apiKey: config.apiKey,
                });
                break;
            case 'claude':
                model = (0, anthropic_1.anthropic)(config.model || 'claude-3-5-sonnet-20241022', {
                    apiKey: config.apiKey,
                });
                break;
            case 'gemini':
                model = (0, google_1.google)(config.model || 'gemini-2.0-flash-exp', {
                    apiKey: config.apiKey,
                });
                break;
            case 'openai':
                model = (0, openai_1.openai)(config.model || 'gpt-4o', {
                    apiKey: config.apiKey,
                });
                break;
            default:
                throw new Error(`Unsupported provider: ${config.provider}`);
        }
        this.models.set(config.provider, model);
    }
    getModel(provider) {
        return this.models.get(provider);
    }
    hasModel(provider) {
        return this.models.has(provider);
    }
    getAvailableProviders() {
        return Array.from(this.models.keys());
    }
}
exports.ModelRegistry = ModelRegistry;
// Default model configurations
exports.DEFAULT_MODELS = {
    grok: 'grok-beta',
    claude: 'claude-3-5-sonnet-20241022',
    gemini: 'gemini-2.0-flash-exp',
    openai: 'gpt-4o',
};
// Default fallback order (Grok -> Claude -> Gemini)
exports.DEFAULT_FALLBACK_ORDER = ['grok', 'claude', 'gemini'];
//# sourceMappingURL=models.js.map