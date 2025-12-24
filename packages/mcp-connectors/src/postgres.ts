import { Pool, PoolClient, QueryResult } from 'pg';

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
export type PostgresToolName =
  | 'query'
  | 'execute'
  | 'transaction'
  | 'get_schema'
  | 'get_table_info';

/**
 * Tool arguments for each Postgres tool
 */
export interface PostgresToolArguments {
  query: { query: string; params?: any[] };
  execute: { query: string; params?: any[] };
  transaction: { queries: Array<{ query: string; params?: any[] }> };
  get_schema: { schema?: string };
  get_table_info: { table: string; schema?: string };
}

/**
 * MCP Connector for PostgreSQL databases
 * Provides database operations with connection pooling and error handling
 */
export class PostgresConnector {
  private pool: Pool;
  private config: PostgresConfig;

  constructor(config: PostgresConfig) {
    this.config = config;
    this.pool = new Pool({
      connectionString: config.connectionString,
      max: config.maxConnections || 20,
      ssl: config.ssl ? { rejectUnauthorized: false } : undefined,
    });
  }

  /**
   * List available tools with their schemas
   */
  async listTools() {
    return {
      tools: [
        {
          name: 'query',
          description: 'Execute a SELECT query and return results',
          inputSchema: {
            type: 'object',
            properties: {
              query: { type: 'string', description: 'SQL SELECT query' },
              params: { type: 'array', description: 'Query parameters (optional)' }
            },
            required: ['query']
          }
        },
        {
          name: 'execute',
          description: 'Execute INSERT, UPDATE, or DELETE statement',
          inputSchema: {
            type: 'object',
            properties: {
              query: { type: 'string', description: 'SQL statement' },
              params: { type: 'array', description: 'Query parameters (optional)' }
            },
            required: ['query']
          }
        },
        {
          name: 'transaction',
          description: 'Execute multiple queries in a transaction',
          inputSchema: {
            type: 'object',
            properties: {
              queries: {
                type: 'array',
                items: {
                  type: 'object',
                  properties: {
                    query: { type: 'string' },
                    params: { type: 'array' }
                  }
                }
              }
            },
            required: ['queries']
          }
        },
        {
          name: 'get_schema',
          description: 'Get database schema information',
          inputSchema: {
            type: 'object',
            properties: {
              schema: { type: 'string', description: 'Schema name (defaults to public)' }
            }
          }
        },
        {
          name: 'get_table_info',
          description: 'Get detailed information about a table',
          inputSchema: {
            type: 'object',
            properties: {
              table: { type: 'string', description: 'Table name' },
              schema: { type: 'string', description: 'Schema name (optional)' }
            },
            required: ['table']
          }
        }
      ]
    };
  }

  /**
   * Execute a tool by name
   */
  async executeTool<T extends PostgresToolName>(
    name: T,
    args: PostgresToolArguments[T]
  ): Promise<any> {
    try {
      switch (name) {
        case 'query':
          return await this.executeQuery(args as PostgresToolArguments['query']);
        case 'execute':
          return await this.executeStatement(args as PostgresToolArguments['execute']);
        case 'transaction':
          return await this.executeTransaction(args as PostgresToolArguments['transaction']);
        case 'get_schema':
          return await this.getSchema(args as PostgresToolArguments['get_schema']);
        case 'get_table_info':
          return await this.getTableInfo(args as PostgresToolArguments['get_table_info']);
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error: any) {
      console.error(`Error executing tool ${name}:`, error);
      throw new Error(`Database operation failed: ${error.message}`);
    }
  }

  private async executeQuery(args: { query: string; params?: any[] }): Promise<QueryResult> {
    const client = await this.pool.connect();
    try {
      return await client.query(args.query, args.params || []);
    } finally {
      client.release();
    }
  }

  private async executeStatement(args: { query: string; params?: any[] }): Promise<{ rowCount: number }> {
    const result = await this.executeQuery(args);
    return { rowCount: result.rowCount || 0 };
  }

  private async executeTransaction(args: { queries: Array<{ query: string; params?: any[] }> }): Promise<{ success: boolean; results: any[] }> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const results = [];
      for (const q of args.queries) {
        const result = await client.query(q.query, q.params || []);
        results.push(result);
      }
      await client.query('COMMIT');
      return { success: true, results };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async getSchema(args: { schema?: string }): Promise<any> {
    const schema = args.schema || 'public';
    const query = `
      SELECT table_name, column_name, data_type
      FROM information_schema.columns
      WHERE table_schema = $1
      ORDER BY table_name, ordinal_position
    `;
    return await this.executeQuery({ query, params: [schema] });
  }

  private async getTableInfo(args: { table: string; schema?: string }): Promise<any> {
    const schema = args.schema || 'public';
    const query = `
      SELECT column_name, data_type, is_nullable, column_default
      FROM information_schema.columns
      WHERE table_schema = $1 AND table_name = $2
      ORDER BY ordinal_position
    `;
    return await this.executeQuery({ query, params: [schema, args.table] });
  }

  /**
   * Close all connections
   */
  async close(): Promise<void> {
    await this.pool.end();
  }
}
