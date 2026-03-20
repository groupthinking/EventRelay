"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SlackConnector = void 0;
const web_api_1 = require("@slack/web-api");
/**
 * MCP Connector for Slack Web API
 * Provides messaging, channel management, and user operations
 */
class SlackConnector {
    client;
    constructor(config) {
        this.client = new web_api_1.WebClient(config.token);
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
    async executeTool(name, args) {
        try {
            switch (name) {
                case 'send_message':
                    return await this.sendMessage(args);
                case 'list_channels':
                    return await this.listChannels(args);
                case 'create_channel':
                    return await this.createChannel(args);
                case 'get_user_info':
                    return await this.getUserInfo(args);
                case 'upload_file':
                    return await this.uploadFile(args);
                case 'get_channel_history':
                    return await this.getChannelHistory(args);
                default:
                    throw new Error(`Unknown tool: ${name}`);
            }
        }
        catch (error) {
            console.error(`Error executing tool ${name}:`, error);
            throw new Error(`Slack API operation failed: ${error.message}`);
        }
    }
    async sendMessage(args) {
        const result = await this.client.chat.postMessage({
            channel: args.channel,
            text: args.text,
            blocks: args.blocks
        });
        return result;
    }
    async listChannels(args) {
        const result = await this.client.conversations.list({
            types: args.types || 'public_channel'
        });
        return result.channels;
    }
    async createChannel(args) {
        const result = await this.client.conversations.create({
            name: args.name,
            is_private: args.is_private || false
        });
        return result.channel;
    }
    async getUserInfo(args) {
        const result = await this.client.users.info({
            user: args.user_id
        });
        return result.user;
    }
    async uploadFile(args) {
        const result = await this.client.files.uploadV2({
            channels: args.channels,
            file: args.file,
            filename: args.filename,
            title: args.title
        });
        return result;
    }
    async getChannelHistory(args) {
        const result = await this.client.conversations.history({
            channel: args.channel,
            limit: args.limit || 100
        });
        return result.messages;
    }
}
exports.SlackConnector = SlackConnector;
//# sourceMappingURL=slack.js.map