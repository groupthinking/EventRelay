import { openai } from '@ai-sdk/openai';
import { anthropic } from '@ai-sdk/anthropic';
import { google } from '@ai-sdk/google';
import type { LanguageModel } from 'ai';
import type { AIProvider, ModelConfig } from './types';

export class ModelRegistry {
  private models = new Map<AIProvider, LanguageModel>();

  constructor(configs: ModelConfig[]) {
    for (const config of configs) {
      this.registerModel(config);
    }
  }

  private registerModel(config: ModelConfig): void {
    let model: LanguageModel;

    switch (config.provider) {
      case 'grok':
        // Grok uses OpenAI-compatible API
        model = openai(config.model || 'grok-beta', {
          baseURL: 'https://api.x.ai/v1',
          apiKey: config.apiKey,
        });
        break;

      case 'claude':
        model = anthropic(config.model || 'claude-3-5-sonnet-20241022', {
          apiKey: config.apiKey,
        });
        break;

      case 'gemini':
        model = google(config.model || 'gemini-2.0-flash-exp', {
          apiKey: config.apiKey,
        });
        break;

      case 'openai':
        model = openai(config.model || 'gpt-4o', {
          apiKey: config.apiKey,
        });
        break;

      case 'liquidai':
        // LiquidAI LFM2-VL is accessed via its MCP HTTP server.
        // We use the OpenAI-compatible shim exposed by the HF Space so
        // that the Vercel AI SDK can drive it through the same interface.
        model = openai(config.model || 'lfm2-vl', {
          baseURL: 'https://liquidai-lfm2-mcp.static.hf.space/v1',
          apiKey: config.apiKey,
        });
        break;

      default:
        throw new Error(`Unsupported provider: ${config.provider}`);
    }

    this.models.set(config.provider, model);
  }

  getModel(provider: AIProvider): LanguageModel | undefined {
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
  claude: 'claude-3-5-sonnet-20241022',
  gemini: 'gemini-2.0-flash-exp',
  openai: 'gpt-4o',
  liquidai: 'lfm2-vl',
};

// Default fallback order (Grok -> Claude -> Gemini -> LiquidAI)
export const DEFAULT_FALLBACK_ORDER: AIProvider[] = ['grok', 'claude', 'gemini', 'liquidai'];
