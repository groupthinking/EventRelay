/**
 * Slack connector configuration
 */
export interface SlackConfig {
    token: string;
}
/**
 * Available Slack tool names
 */
export type SlackToolName = 'send_message' | 'list_channels' | 'create_channel' | 'get_user_info' | 'upload_file' | 'get_channel_history';
/**
 * Tool arguments for each Slack tool
 */
export interface SlackToolArguments {
    send_message: {
        channel: string;
        text: string;
        blocks?: any[];
    };
    list_channels: {
        types?: string;
    };
    create_channel: {
        name: string;
        is_private?: boolean;
    };
    get_user_info: {
        user_id: string;
    };
    upload_file: {
        channels: string;
        file: Buffer;
        filename: string;
        title?: string;
    };
    get_channel_history: {
        channel: string;
        limit?: number;
    };
}
/**
 * MCP Connector for Slack Web API
 * Provides messaging, channel management, and user operations
 */
export declare class SlackConnector {
    private client;
    constructor(config: SlackConfig);
    /**
     * List available tools with their schemas
     */
    listTools(): Promise<{
        tools: ({
            name: string;
            description: string;
            inputSchema: {
                type: string;
                properties: {
                    channel: {
                        type: string;
                        description: string;
                    };
                    text: {
                        type: string;
                        description: string;
                    };
                    blocks: {
                        type: string;
                        description: string;
                    };
                    types?: undefined;
                    name?: undefined;
                    is_private?: undefined;
                    user_id?: undefined;
                    channels?: undefined;
                    file?: undefined;
                    filename?: undefined;
                    title?: undefined;
                    limit?: undefined;
                };
                required: string[];
            };
        } | {
            name: string;
            description: string;
            inputSchema: {
                type: string;
                properties: {
                    types: {
                        type: string;
                        description: string;
                        default: string;
                    };
                    channel?: undefined;
                    text?: undefined;
                    blocks?: undefined;
                    name?: undefined;
                    is_private?: undefined;
                    user_id?: undefined;
                    channels?: undefined;
                    file?: undefined;
                    filename?: undefined;
                    title?: undefined;
                    limit?: undefined;
                };
                required?: undefined;
            };
        } | {
            name: string;
            description: string;
            inputSchema: {
                type: string;
                properties: {
                    name: {
                        type: string;
                        description: string;
                    };
                    is_private: {
                        type: string;
                        default: boolean;
                    };
                    channel?: undefined;
                    text?: undefined;
                    blocks?: undefined;
                    types?: undefined;
                    user_id?: undefined;
                    channels?: undefined;
                    file?: undefined;
                    filename?: undefined;
                    title?: undefined;
                    limit?: undefined;
                };
                required: string[];
            };
        } | {
            name: string;
            description: string;
            inputSchema: {
                type: string;
                properties: {
                    user_id: {
                        type: string;
                        description: string;
                    };
                    channel?: undefined;
                    text?: undefined;
                    blocks?: undefined;
                    types?: undefined;
                    name?: undefined;
                    is_private?: undefined;
                    channels?: undefined;
                    file?: undefined;
                    filename?: undefined;
                    title?: undefined;
                    limit?: undefined;
                };
                required: string[];
            };
        } | {
            name: string;
            description: string;
            inputSchema: {
                type: string;
                properties: {
                    channels: {
                        type: string;
                        description: string;
                    };
                    file: {
                        type: string;
                        description: string;
                    };
                    filename: {
                        type: string;
                        description: string;
                    };
                    title: {
                        type: string;
                        description: string;
                    };
                    channel?: undefined;
                    text?: undefined;
                    blocks?: undefined;
                    types?: undefined;
                    name?: undefined;
                    is_private?: undefined;
                    user_id?: undefined;
                    limit?: undefined;
                };
                required: string[];
            };
        } | {
            name: string;
            description: string;
            inputSchema: {
                type: string;
                properties: {
                    channel: {
                        type: string;
                        description: string;
                    };
                    limit: {
                        type: string;
                        default: number;
                    };
                    text?: undefined;
                    blocks?: undefined;
                    types?: undefined;
                    name?: undefined;
                    is_private?: undefined;
                    user_id?: undefined;
                    channels?: undefined;
                    file?: undefined;
                    filename?: undefined;
                    title?: undefined;
                };
                required: string[];
            };
        })[];
    }>;
    /**
     * Execute a tool by name
     */
    executeTool<T extends SlackToolName>(name: T, args: SlackToolArguments[T]): Promise<any>;
    private sendMessage;
    private listChannels;
    private createChannel;
    private getUserInfo;
    private uploadFile;
    private getChannelHistory;
}
