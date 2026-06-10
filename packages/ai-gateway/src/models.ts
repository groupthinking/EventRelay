import { createOpenAI } from '@ai-sdk/openai';
import { createAnthropic } from '@ai-sdk/anthropic';
import { createGoogleGenerativeAI } from '@ai-sdk/google';
import type { LanguageModel } from 'ai';
import type { AIProvider, ModelConfig } from './types';

export interface RegisteredModel {
  model: LanguageModel;
  modelId: string;
}

export class ModelRegistry {
  private models = new Map<AIProvider, RegisteredModel>();

  constructor(configs: ModelConfig[]) {
    for (const config of configs) {
      this.registerModel(config);
    }
  }

  private registerModel(config: ModelConfig): void {
    const modelId = config.model || DEFAULT_MODELS[config.provider];
    let model: LanguageModel;

    switch (config.provider) {
      case 'grok':
        // Grok uses OpenAI-compatible API
        model = createOpenAI({
          baseURL: 'https://api.x.ai/v1',
          apiKey: config.apiKey,
        })(modelId);
        break;

      case 'claude':
        model = createAnthropic({
          apiKey: config.apiKey,
        })(modelId);
        break;

      case 'gemini':
        model = createGoogleGenerativeAI({
          apiKey: config.apiKey,
        })(modelId);
        break;

      case 'openai':
        model = createOpenAI({
          apiKey: config.apiKey,
        })(modelId);
        break;

      default:
        throw new Error(`Unsupported provider: ${config.provider}`);
    }

    this.models.set(config.provider, { model, modelId });
  }

  getModel(provider: AIProvider): RegisteredModel | undefined {
    return this.models.get(provider);
  }

  hasModel(provider: AIProvider): boolean {
    return this.models.has(provider);
  }

  getAvailableProviders(): AIProvider[] {
    return Array.from(this.models.keys());
  }
}

// Default model configurations
export const DEFAULT_MODELS: Record<AIProvider, string> = {
  grok: 'grok-beta',
  claude: 'claude-opus-4-8',
  gemini: 'gemini-2.0-flash-exp',
  openai: 'gpt-4o',
};

// Default fallback order (Grok -> Claude -> Gemini)
export const DEFAULT_FALLBACK_ORDER: AIProvider[] = ['grok', 'claude', 'gemini'];
