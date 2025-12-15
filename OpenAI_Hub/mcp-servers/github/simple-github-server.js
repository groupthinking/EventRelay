#!/usr/bin/env node

const https = require('https');

// Get GitHub token from environment variable
const GITHUB_TOKEN = process.env.GITHUB_PERSONAL_ACCESS_TOKEN;
if (!GITHUB_TOKEN) {
  console.error('Error: GITHUB_PERSONAL_ACCESS_TOKEN not set');
  process.exit(1);
}

// Simple implementation of a GitHub API MCP server
// This implements the MCP protocol directly over stdio

let requestCounter = 1;

// Read from stdin
process.stdin.on('data', (buffer) => {
  const data = buffer.toString();
  try {
    // Parse JSON-RPC request
    const request = JSON.parse(data);
    
    // Handle JSON-RPC request
    handleRequest(request);
  } catch (err) {
    console.error('Error processing request:', err);
    sendErrorResponse(null, -32700, 'Parse error');
  }
});

// Handle JSON-RPC request
async function handleRequest(request) {
  const { id, method, params } = request;
  
  try {
    switch (method) {
      case 'list_tools':
        // List available tools
        sendResponse(id, {
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
        });
        break;
        
      case 'call_tool':
        if (!params.name) {
          sendErrorResponse(id, -32602, 'Invalid params: missing name');
          return;
        }
        
        switch (params.name) {
          case 'search_repositories':
            // Search for repositories
            if (!params.arguments || !params.arguments.query) {
              sendErrorResponse(id, -32602, 'Invalid params: missing query');
              return;
            }
            
            try {
              const result = await searchRepositories(
                params.arguments.query,
                params.arguments.page || 1,
                params.arguments.perPage || 30
              );
              
              sendResponse(id, {
                content: [
                  {
                    type: 'text',
                    text: JSON.stringify(result, null, 2)
                  }
                ]
              });
            } catch (error) {
              sendErrorResponse(id, -32000, error.message);
            }
            break;
            
          case 'get_repository':
            // Get repository details
            if (!params.arguments || !params.arguments.owner || !params.arguments.repo) {
              sendErrorResponse(id, -32602, 'Invalid params: missing owner or repo');
              return;
            }
            
            try {
              const result = await getRepository(
                params.arguments.owner,
                params.arguments.repo
              );
              
              sendResponse(id, {
                content: [
                  {
                    type: 'text',
                    text: JSON.stringify(result, null, 2)
                  }
                ]
              });
            } catch (error) {
              sendErrorResponse(id, -32000, error.message);
            }
            break;
            
          default:
            sendErrorResponse(id, -32601, `Method not found: ${params.name}`);
        }
        break;
        
      default:
        sendErrorResponse(id, -32601, `Method not found: ${method}`);
    }
  } catch (error) {
    sendErrorResponse(id, -32000, `Internal error: ${error.message}`);
  }
}

// Send JSON-RPC response
function sendResponse(id, result) {
  const response = {
    jsonrpc: '2.0',
    id,
    result
  };
  
  process.stdout.write(JSON.stringify(response) + '\n');
}

// Send JSON-RPC error response
function sendErrorResponse(id, code, message) {
  const response = {
    jsonrpc: '2.0',
    id,
    error: {
      code,
      message
    }
  };
  
  process.stdout.write(JSON.stringify(response) + '\n');
}

// GitHub API helpers
function searchRepositories(query, page = 1, perPage = 30) {
  return makeGitHubRequest(
    'GET',
    `/search/repositories?q=${encodeURIComponent(query)}&page=${page}&per_page=${perPage}`
  );
}

function getRepository(owner, repo) {
  return makeGitHubRequest('GET', `/repos/${owner}/${repo}`);
}

function makeGitHubRequest(method, path, data = null) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.github.com',
      path,
      method,
      headers: {
        'User-Agent': 'GitHub-MCP-Server',
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

// Notify that the server is ready
console.error('GitHub MCP server running on stdio');
