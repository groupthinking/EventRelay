import type { LanguageModel } from 'ai';
import type { AIProvider, ModelConfig } from './types';
export declare class ModelRegistry {
    private models;
    constructor(configs: ModelConfig[]);
    private registerModel;
    getModel(provider: AIProvider): LanguageModel | undefined;
    hasModel(provider: AIProvider): boolean;
    getAvailableProviders(): AIProvider[];
}
export declare const DEFAULT_MODELS: Record<AIProvider, string>;
export declare const DEFAULT_FALLBACK_ORDER: AIProvider[];
