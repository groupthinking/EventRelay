export type AIProvider = 'grok' | 'claude' | 'gemini' | 'openai';

export interface AIGatewayConfig {
  providers: AIProvider[];
  fallbackOrder?: AIProvider[];
  maxRetries?: number;
  timeout?: number;
}

export interface ModelConfig {
  provider: AIProvider;
  model: string;
  apiKey: string;
  maxTokens?: number;
  temperature?: number;
}

export interface GenerateOptions {
  prompt: string;
  system?: string;
  maxTokens?: number;
  temperature?: number;
  stream?: boolean;
}

export interface GenerateResult {
  text: string;
  provider: AIProvider;
  model: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

export interface StreamResult {
  textStream: AsyncIterable<string>;
  provider: AIProvider;
  model: string;
}
