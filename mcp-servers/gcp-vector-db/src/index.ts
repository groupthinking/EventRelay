#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from "@modelcontextprotocol/sdk/types.js";
import pg from "pg";
import { z } from "zod";

const { Client } = pg;

// Environment variable validation can happen here or assume provided in environment
const DB_CONFIG = {
  connectionString: process.env.DATABASE_URL,
  ssl: {
      rejectUnauthorized: false
  }
};

class VectorDbServer {
  private server: Server;
  private db: pg.Client | null = null;

  constructor() {
    this.server = new Server(
      {
        name: "gcp-vector-db",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupHandlers();

    // Error handling
    this.server.onerror = (error) => console.error("[MCP Error]", error);
  }

  private async getDb() {
    if (!this.db) {
      if (!process.env.DATABASE_URL) {
         throw new McpError(ErrorCode.InvalidParams, "DATABASE_URL environment variable is not set");
      }
      this.db = new Client(DB_CONFIG);
      await this.db.connect();
    }
    return this.db;
  }

  private setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: "init_vector_extension",
          description: "Enable the pgvector extension and create the items schema in the database.",
          inputSchema: {
            type: "object",
            properties: {},
          },
        },
        {
          name: "store_item",
          description: "Store a text item with its vector embedding.",
          inputSchema: {
            type: "object",
            properties: {
              content: { type: "string", description: "The text content to store" },
              vector: {
                type: "array",
                items: { type: "number" },
                description: "Array of floating point numbers representing the vector embedding"
              },
              metadata: { type: "string", description: "JSON string metadata (optional)" }
            },
            required: ["content", "vector"],
          },
        },
        {
          name: "search_similar",
          description: "Search for similar items using a query vector.",
          inputSchema: {
            type: "object",
            properties: {
              vector: {
                type: "array",
                items: { type: "number" },
                description: "Query vector"
              },
              limit: { type: "number", description: "Number of results to return (default 5)" },
              threshold: { type: "number", description: "Similarity threshold (default 0.7)" }
            },
            required: ["vector"],
          },
        },
        {
            name: "execute_sql",
            description: "Execute a raw SQL query (Admin use only)",
            inputSchema: {
                type: "object",
                properties: {
                    query: { type: "string" }
                },
                required: ["query"]
            }
        }
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const client = await this.getDb();

      switch (request.params.name) {
        case "init_vector_extension": {
          try {
            await client.query("CREATE EXTENSION IF NOT EXISTS vector;");
            await client.query(`
              CREATE TABLE IF NOT EXISTS vector_items (
                id SERIAL PRIMARY KEY,
                content TEXT,
                embedding vector(1536),
                metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
              );
            `);
            return {
              content: [{ type: "text", text: "Successfully enabled pgvector and created 'vector_items' table." }],
            };
          } catch (error: any) {
            return {
                content: [{ type: "text", text: `Error initializing: ${error.message}` }],
                isError: true
            };
          }
        }

        case "store_item": {
            const { content, vector, metadata } = request.params.arguments as any;
            const vectorStr = JSON.stringify(vector);
            const meta = metadata ? metadata : "{}";

            try {
                // simple validation
                if (!Array.isArray(vector)) throw new Error("Vector must be an array");

                await client.query(
                    "INSERT INTO vector_items (content, embedding, metadata) VALUES ($1, $2, $3)",
                    [content, vectorStr, meta]
                );
                return {
                    content: [{ type: "text", text: "Item stored successfully." }],
                };
            } catch (error: any) {
                return {
                    content: [{ type: "text", text: `Error storing item: ${error.message}` }],
                    isError: true
                };
            }
        }

        case "search_similar": {
            const { vector, limit = 5, threshold = 0 } = request.params.arguments as any;
            const vectorStr = JSON.stringify(vector);

            try {
                 // <-> is Euclidean distance, <=> is Cosine distance, <#> is negative inner product.
                 // Usually for cosine similarity we use <=> (cosine distance).
                 // Distance = 1 - Similarity. So for similarity search we sort by distance ASC.
                 const res = await client.query(
                    `SELECT id, content, metadata, 1 - (embedding <=> $1) as similarity
                     FROM vector_items
                     WHERE 1 - (embedding <=> $1) > $2
                     ORDER BY similarity DESC
                     LIMIT $3`,
                    [vectorStr, threshold, limit]
                 );

                 const results = res.rows.map(row => ({
                     id: row.id,
                     content: row.content,
                     similarity: row.similarity,
                     metadata: row.metadata
                 }));

                 return {
                     content: [{ type: "text", text: JSON.stringify(results, null, 2) }]
                 };

            } catch (error: any) {
                return {
                    content: [{ type: "text", text: `Error searching: ${error.message}` }],
                    isError: true
                };
            }
        }

        case "execute_sql": {
             const { query } = request.params.arguments as any;
             try {
                 const res = await client.query(query);
                 return {
                     content: [{ type: "text", text: JSON.stringify(res.rows, null, 2) }]
                 };
             } catch (error: any) {
                 return {
                     content: [{ type: "text", text: `SQL Error: ${error.message}` }],
                     isError: true
                 };
             }
        }

        default:
          throw new McpError(
            ErrorCode.MethodNotFound,
            `Unknown tool: ${request.params.name}`
          );
      }
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("GCP Vector DB MCP server running on stdio");
  }
}

const server = new VectorDbServer();
server.run().catch(console.error);
