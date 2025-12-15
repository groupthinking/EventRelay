import { generateText, streamText } from 'ai';
import { ModelRegistry, DEFAULT_FALLBACK_ORDER } from './models';
import type {
  AIProvider,
  AIGatewayConfig,
  ModelConfig,
  GenerateOptions,
  GenerateResult,
  StreamResult,
} from './types';

export class AIGateway {
  private registry: ModelRegistry;
  private fallbackOrder: AIProvider[];
  private maxRetries: number;
  private timeout: number;

  constructor(configs: ModelConfig[], options?: Partial<AIGatewayConfig>) {
    this.registry = new ModelRegistry(configs);
    this.fallbackOrder = options?.fallbackOrder || DEFAULT_FALLBACK_ORDER;
    this.maxRetries = options?.maxRetries || 3;
    this.timeout = options?.timeout || 30000;
  }

  /**
   * Generate text with automatic failover between providers
   */
  async generate(options: GenerateOptions): Promise<GenerateResult> {
    const errors: Array<{ provider: AIProvider; error: Error }> = [];

    for (const provider of this.fallbackOrder) {
      if (!this.registry.hasModel(provider)) {
        continue;
      }

      try {
        const model = this.registry.getModel(provider);
        if (!model) continue;

        const result = await this.generateWithTimeout(model, provider, options);
        return result;
      } catch (error) {
        errors.push({
          provider,
          error: error instanceof Error ? error : new Error(String(error)),
        });
        console.warn(`[AIGateway] ${provider} failed, trying next provider...`, error);
      }
    }

    // All providers failed
    throw new Error(
      `All providers failed: ${errors.map((e) => `${e.provider}: ${e.error.message}`).join(', ')}`
    );
  }

  /**
   * Stream text with automatic failover
   */
  async stream(options: GenerateOptions): Promise<StreamResult> {
    const errors: Array<{ provider: AIProvider; error: Error }> = [];

    for (const provider of this.fallbackOrder) {
      if (!this.registry.hasModel(provider)) {
        continue;
      }

      try {
        const model = this.registry.getModel(provider);
        if (!model) continue;

        const { textStream } = await streamText({
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
      } catch (error) {
        errors.push({
          provider,
          error: error instanceof Error ? error : new Error(String(error)),
        });
        console.warn(`[AIGateway] ${provider} stream failed, trying next provider...`, error);
      }
    }

    throw new Error(
      `All providers failed for streaming: ${errors.map((e) => `${e.provider}: ${e.error.message}`).join(', ')}`
    );
  }

  /**
   * Generate with timeout enforcement
   */
  private async generateWithTimeout(
    model: any,
    provider: AIProvider,
    options: GenerateOptions
  ): Promise<GenerateResult> {
    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('Request timeout')), this.timeout)
    );

    const generatePromise = generateText({
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
  getAvailableProviders(): AIProvider[] {
    return this.registry.getAvailableProviders();
  }

  /**
   * Check if provider is available
   */
  hasProvider(provider: AIProvider): boolean {
    return this.registry.hasModel(provider);
  }
}

// Export types
export type {
  AIProvider,
  AIGatewayConfig,
  ModelConfig,
  GenerateOptions,
  GenerateResult,
  StreamResult,
} from './types';

// Export model utilities
export { ModelRegistry, DEFAULT_MODELS, DEFAULT_FALLBACK_ORDER } from './models';
