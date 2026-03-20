import type { AIProvider, AIGatewayConfig, ModelConfig, GenerateOptions, GenerateResult, StreamResult } from './types';
export declare class AIGateway {
    private registry;
    private fallbackOrder;
    private maxRetries;
    private timeout;
    constructor(configs: ModelConfig[], options?: Partial<AIGatewayConfig>);
    /**
     * Generate text with automatic failover between providers
     */
    generate(options: GenerateOptions): Promise<GenerateResult>;
    /**
     * Stream text with automatic failover
     */
    stream(options: GenerateOptions): Promise<StreamResult>;
    /**
     * Generate with timeout enforcement
     */
    private generateWithTimeout;
    /**
     * Get available providers
     */
    getAvailableProviders(): AIProvider[];
    /**
     * Check if provider is available
     */
    hasProvider(provider: AIProvider): boolean;
}
export type { AIProvider, AIGatewayConfig, ModelConfig, GenerateOptions, GenerateResult, StreamResult, } from './types';
export { ModelRegistry, DEFAULT_MODELS, DEFAULT_FALLBACK_ORDER } from './models';
