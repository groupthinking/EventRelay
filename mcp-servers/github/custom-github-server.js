#!/usr/bin/env node

const sdk = require('@modelcontextprotocol/sdk');
const Server = sdk.Server;
const StdioServerTransport = sdk.StdioServerTransport;
const CallToolRequestSchema = sdk.Types.CallToolRequestSchema;
const ErrorCode = sdk.Types.ErrorCode;
const ListToolsRequestSchema = sdk.Types.ListToolsRequestSchema; 
const McpError = sdk.Types.McpError;

const https = require('https');

// Get the GitHub Personal Access Token from environment variables
const GITHUB_TOKEN = process.env.GITHUB_PERSONAL_ACCESS_TOKEN || process.env.GITHUB_TOKEN;

if (!GITHUB_TOKEN) {
  console.error('Error: GITHUB_PERSONAL_ACCESS_TOKEN or GITHUB_TOKEN environment variable is required');
  process.exit(1);
}

// Simple GitHub API client
function githubApiRequest(method, path, data = null) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.github.com',
      path,
      method,
      headers: {
        'User-Agent': 'MCP-GitHub-Server',
        'Authorization': `token ${GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
      }
    };

    const req = https.request(options, (res) => {
      let responseData = '';
      
      res.on('data', (chunk) => {
        responseData += chunk;
      });
      
      res.on('end', () => {
        try {
          const parsedData = JSON.parse(responseData);
          
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(parsedData);
          } else {
            reject(new Error(`GitHub API error: ${parsedData.message || 'Unknown error'}`));
          }
        } catch (e) {
          reject(new Error(`Failed to parse GitHub API response: ${e.message}`));
        }
      });
    });
    
    req.on('error', (error) => {
      reject(error);
    });
    
    if (data) {
      req.write(JSON.stringify(data));
    }
    
    req.end();
  });
}

class GitHubMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'github-mcp-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    
    // Error handling
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    
    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  setupToolHandlers() {
    // Define available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'search_repositories',
          description: 'Search for GitHub repositories',
          inputSchema: {
            type: 'object',
            properties: {
              query: {
                type: 'string',
                description: 'Search query'
              },
              page: {
                type: 'number',
                description: 'Page number for pagination'
              },
              perPage: {
                type: 'number',
                description: 'Results per page (max 100)'
              }
            },
            required: ['query']
          }
        },
        {
          name: 'get_repository',
          description: 'Get details about a GitHub repository',
          inputSchema: {
            type: 'object',
            properties: {
              owner: {
                type: 'string',
                description: 'Repository owner (username or organization)'
              },
              repo: {
                type: 'string',
                description: 'Repository name'
              }
            },
            required: ['owner', 'repo']
          }
        }
      ]
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      try {
        switch (request.params.name) {
          case 'search_repositories':
            return await this.searchRepositories(request.params.arguments);
          case 'get_repository':
            return await this.getRepository(request.params.arguments);
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${request.params.name}`
            );
        }
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Error: ${error.message}`
            }
          ],
          isError: true
        };
      }
    });
  }

  async searchRepositories({ query, page = 1, perPage = 30 }) {
    try {
      const results = await githubApiRequest(
        'GET',
        `/search/repositories?q=${encodeURIComponent(query)}&page=${page}&per_page=${perPage}`
      );
      
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(results, null, 2)
          }
        ]
      };
    } catch (error) {
      throw error;
    }
  }

  async getRepository({ owner, repo }) {
    try {
      const repository = await githubApiRequest('GET', `/repos/${owner}/${repo}`);
      
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(repository, null, 2)
          }
        ]
      };
    } catch (error) {
      throw error;
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('GitHub MCP server running on stdio');
  }
}

// Start the server
const server = new GitHubMCPServer();
server.run().catch(console.error);
