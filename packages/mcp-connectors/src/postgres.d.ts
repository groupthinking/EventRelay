/**
 * Postgres connector configuration
 */
export interface PostgresConfig {
    connectionString: string;
    maxConnections?: number;
    ssl?: boolean;
}
/**
 * Available Postgres tool names
 */
export type PostgresToolName = 'query' | 'execute' | 'transaction' | 'get_schema' | 'get_table_info';
/**
 * Tool arguments for each Postgres tool
 */
export interface PostgresToolArguments {
    query: {
        query: string;
        params?: any[];
    };
    execute: {
        query: string;
        params?: any[];
    };
    transaction: {
        queries: Array<{
            query: string;
            params?: any[];
        }>;
    };
    get_schema: {
        schema?: string;
    };
    get_table_info: {
        table: string;
        schema?: string;
    };
}
/**
 * MCP Connector for PostgreSQL databases
 * Provides database operations with connection pooling and error handling
 */
export declare class PostgresConnector {
    private pool;
    private config;
    constructor(config: PostgresConfig);
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
                    query: {
                        type: string;
                        description: string;
                    };
                    params: {
                        type: string;
                        description: string;
                    };
                    queries?: undefined;
                    schema?: undefined;
                    table?: undefined;
                };
                required: string[];
            };
        } | {
            name: string;
            description: string;
            inputSchema: {
                type: string;
                properties: {
                    queries: {
                        type: string;
                        items: {
                            type: string;
                            properties: {
                                query: {
                                    type: string;
                                };
                                params: {
                                    type: string;
                                };
                            };
                        };
                    };
                    query?: undefined;
                    params?: undefined;
                    schema?: undefined;
                    table?: undefined;
                };
                required: string[];
            };
        } | {
            name: string;
            description: string;
            inputSchema: {
                type: string;
                properties: {
                    schema: {
                        type: string;
                        description: string;
                    };
                    query?: undefined;
                    params?: undefined;
                    queries?: undefined;
                    table?: undefined;
                };
                required?: undefined;
            };
        } | {
            name: string;
            description: string;
            inputSchema: {
                type: string;
                properties: {
                    table: {
                        type: string;
                        description: string;
                    };
                    schema: {
                        type: string;
                        description: string;
                    };
                    query?: undefined;
                    params?: undefined;
                    queries?: undefined;
                };
                required: string[];
            };
        })[];
    }>;
    /**
     * Execute a tool by name
     */
    executeTool<T extends PostgresToolName>(name: T, args: PostgresToolArguments[T]): Promise<any>;
    private executeQuery;
    private executeStatement;
    private executeTransaction;
    private getSchema;
    private getTableInfo;
    /**
     * Close all connections
     */
    close(): Promise<void>;
}
