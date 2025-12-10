declare module 'anthropic' {
  export interface AnthropicOptions {
    apiKey: string;
    baseURL?: string;
  }

  export interface MessageParams {
    model: string;
    max_tokens: number;
    messages: Array<{
      role: 'user' | 'assistant';
      content: string;
    }>;
  }

  export interface MessageResponse {
    content: Array<{
      text: string;
      type: string;
    }>;
  }

  export default class Anthropic {
    constructor(options: AnthropicOptions);
    
    messages: {
      create(params: MessageParams): Promise<MessageResponse>;
    };
  }
}
