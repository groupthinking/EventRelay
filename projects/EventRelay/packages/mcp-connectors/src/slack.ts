import { WebClient } from '@slack/web-api';

/**
 * Slack connector configuration
 */
export interface SlackConfig {
  token: string;
}

/**
 * Available Slack tool names
 */
export type SlackToolName =
  | 'send_message'
  | 'list_channels'
  | 'create_channel'
  | 'get_user_info'
  | 'upload_file'
  | 'get_channel_history';

/**
 * Tool arguments for each Slack tool
 */
export interface SlackToolArguments {
  send_message: { channel: string; text: string; blocks?: any[] };
  list_channels: { types?: string };
  create_channel: { name: string; is_private?: boolean };
  get_user_info: { user_id: string };
  upload_file: { channels: string; file: Buffer; filename: string; title?: string };
  get_channel_history: { channel: string; limit?: number };
}

/**
 * MCP Connector for Slack Web API
 * Provides messaging, channel management, and user operations
 */
export class SlackConnector {
  private client: WebClient;

  constructor(config: SlackConfig) {
    this.client = new WebClient(config.token);
  }

  /**
   * List available tools with their schemas
   */
  async listTools() {
    return {
      tools: [
        {
          name: 'send_message',
          description: 'Send a message to a channel',
          inputSchema: {
            type: 'object',
            properties: {
              channel: { type: 'string', description: 'Channel ID or name' },
              text: { type: 'string', description: 'Message text' },
              blocks: { type: 'array', description: 'Block Kit blocks (optional)' }
            },
            required: ['channel', 'text']
          }
        },
        {
          name: 'list_channels',
          description: 'List workspace channels',
          inputSchema: {
            type: 'object',
            properties: {
              types: { type: 'string', description: 'Channel types (public_channel, private_channel, etc.)', default: 'public_channel' }
            }
          }
        },
        {
          name: 'create_channel',
          description: 'Create a new channel',
          inputSchema: {
            type: 'object',
            properties: {
              name: { type: 'string', description: 'Channel name' },
              is_private: { type: 'boolean', default: false }
            },
            required: ['name']
          }
        },
        {
          name: 'get_user_info',
          description: 'Get information about a user',
          inputSchema: {
            type: 'object',
            properties: {
              user_id: { type: 'string', description: 'User ID' }
            },
            required: ['user_id']
          }
        },
        {
          name: 'upload_file',
          description: 'Upload a file to a channel',
          inputSchema: {
            type: 'object',
            properties: {
              channels: { type: 'string', description: 'Comma-separated channel IDs' },
              file: { type: 'string', description: 'File buffer' },
              filename: { type: 'string', description: 'File name' },
              title: { type: 'string', description: 'File title (optional)' }
            },
            required: ['channels', 'file', 'filename']
          }
        },
        {
          name: 'get_channel_history',
          description: 'Get message history from a channel',
          inputSchema: {
            type: 'object',
            properties: {
              channel: { type: 'string', description: 'Channel ID' },
              limit: { type: 'number', default: 100 }
            },
            required: ['channel']
          }
        }
      ]
    };
  }

  /**
   * Execute a tool by name
   */
  async executeTool<T extends SlackToolName>(
    name: T,
    args: SlackToolArguments[T]
  ): Promise<any> {
    try {
      switch (name) {
        case 'send_message':
          return await this.sendMessage(args as SlackToolArguments['send_message']);
        case 'list_channels':
          return await this.listChannels(args as SlackToolArguments['list_channels']);
        case 'create_channel':
          return await this.createChannel(args as SlackToolArguments['create_channel']);
        case 'get_user_info':
          return await this.getUserInfo(args as SlackToolArguments['get_user_info']);
        case 'upload_file':
          return await this.uploadFile(args as SlackToolArguments['upload_file']);
        case 'get_channel_history':
          return await this.getChannelHistory(args as SlackToolArguments['get_channel_history']);
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error: any) {
      console.error(`Error executing tool ${name}:`, error);
      throw new Error(`Slack API operation failed: ${error.message}`);
    }
  }

  private async sendMessage(args: { channel: string; text: string; blocks?: any[] }) {
    const result = await this.client.chat.postMessage({
      channel: args.channel,
      text: args.text,
      blocks: args.blocks
    });
    return result;
  }

  private async listChannels(args: { types?: string }) {
    const result = await this.client.conversations.list({
      types: args.types || 'public_channel'
    });
    return result.channels;
  }

  private async createChannel(args: { name: string; is_private?: boolean }) {
    const result = await this.client.conversations.create({
      name: args.name,
      is_private: args.is_private || false
    });
    return result.channel;
  }

  private async getUserInfo(args: { user_id: string }) {
    const result = await this.client.users.info({
      user: args.user_id
    });
    return result.user;
  }

  private async uploadFile(args: { channels: string; file: Buffer; filename: string; title?: string }) {
    const result = await this.client.files.uploadV2({
      channels: args.channels,
      file: args.file,
      filename: args.filename,
      title: args.title
    });
    return result;
  }

  private async getChannelHistory(args: { channel: string; limit?: number }) {
    const result = await this.client.conversations.history({
      channel: args.channel,
      limit: args.limit || 100
    });
    return result.messages;
  }
}
