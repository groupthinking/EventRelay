/**
 * GitHub MCP Extractor
 * 
 * This script extracts repository data from GitHub and sends it to the MCP endpoint.
 * It can use the real GitHub API or mock data for demonstration.
 */

// Using modern import syntax for node-fetch
const { default: fetch } = require('node-fetch');

// Supabase MCP endpoint
const MCP_ENDPOINT = 'https://nsfrhirwsjqwhagtuaxx.supabase.co/functions/v1/connect-to-cursor-mcp';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5zZnJoaXJ3c2pxd2hhZ3R1YXh4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDYyMTcwMTMsImV4cCI6MjA2MTc5MzAxM30.mvPT1ha9keOLFCxVPoUoAwWt2uKb-m_ii2bu2I-ziyk';

/**
 * GitHub API client - can be real or mock
 */
class GitHubAPI {
  constructor(options = {}) {
    this.useMock = options.useMock || false;
    this.token = options.token || process.env.GITHUB_TOKEN;
  }
  
  /**
   * Get repository contents
   */
  async getContents(owner, repo, path = '', ref = 'main') {
    if (this.useMock) {
      return this._getMockContents(owner, repo, path, ref);
    }
    
    // Real GitHub API call
    const url = `https://api.github.com/repos/${owner}/${repo}/contents/${path}?ref=${ref}`;
    const response = await fetch(url, {
      headers: {
        'Authorization': `token ${this.token}`,
        'Accept': 'application/vnd.github.v3+json'
      }
    });
    
    if (!response.ok) {
      throw new Error(`GitHub API error: ${response.status} - ${await response.text()}`);
    }
    
    return await response.json();
  }
  
  /**
   * Get repository information
   */
  async getRepo(owner, repo) {
    if (this.useMock) {
      return this._getMockRepo(owner, repo);
    }
    
    // Real GitHub API call
    const url = `https://api.github.com/repos/${owner}/${repo}`;
    const response = await fetch(url, {
      headers: {
        'Authorization': `token ${this.token}`,
        'Accept': 'application/vnd.github.v3+json'
      }
    });
    
    if (!response.ok) {
      throw new Error(`GitHub API error: ${response.status} - ${await response.text()}`);
    }
    
    return await response.json();
  }
  
  /**
   * Get recent commits
   */
  async getCommits(owner, repo, branch = 'main', limit = 10) {
    if (this.useMock) {
      return this._getMockCommits(owner, repo, branch, limit);
    }
    
    // Real GitHub API call
    const url = `https://api.github.com/repos/${owner}/${repo}/commits?sha=${branch}&per_page=${limit}`;
    const response = await fetch(url, {
      headers: {
        'Authorization': `token ${this.token}`,
        'Accept': 'application/vnd.github.v3+json'
      }
    });
    
    if (!response.ok) {
      throw new Error(`GitHub API error: ${response.status} - ${await response.text()}`);
    }
    
    return await response.json();
  }
  
  /**
   * Generate mock contents data 
   */
  async _getMockContents(owner, repo, path, ref) {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 300));
    
    if (path === '') {
      // Root directory
      return [
        {
          name: 'src',
          path: 'src',
          type: 'dir',
          sha: 'abc123',
          url: `https://api.github.com/repos/${owner}/${repo}/contents/src?ref=${ref}`
        },
        {
          name: 'package.json',
          path: 'package.json',
          type: 'file',
          sha: 'def456',
          size: 1024,
          url: `https://api.github.com/repos/${owner}/${repo}/contents/package.json?ref=${ref}`,
          download_url: `https://raw.githubusercontent.com/${owner}/${repo}/${ref}/package.json`
        },
        {
          name: 'README.md',
          path: 'README.md',
          type: 'file',
          sha: 'ghi789',
          size: 2048,
          url: `https://api.github.com/repos/${owner}/${repo}/contents/README.md?ref=${ref}`,
          download_url: `https://raw.githubusercontent.com/${owner}/${repo}/${ref}/README.md`,
          content: Buffer.from('# Mock Repository\n\nThis is a mock repository for testing the MCP GitHub extractor.').toString('base64'),
          encoding: 'base64'
        }
      ];
    } else if (path === 'src') {
      // src directory
      return [
        {
          name: 'index.js',
          path: 'src/index.js',
          type: 'file',
          sha: 'jkl012',
          size: 512,
          url: `https://api.github.com/repos/${owner}/${repo}/contents/src/index.js?ref=${ref}`,
          download_url: `https://raw.githubusercontent.com/${owner}/${repo}/${ref}/src/index.js`,
          content: Buffer.from('console.log("Hello MCP!");').toString('base64'),
          encoding: 'base64'
        },
        {
          name: 'utils',
          path: 'src/utils',
          type: 'dir',
          sha: 'mno345',
          url: `https://api.github.com/repos/${owner}/${repo}/contents/src/utils?ref=${ref}`
        }
      ];
    } else if (path === 'package.json') {
      // Single file
      return {
        name: 'package.json',
        path: 'package.json',
        type: 'file',
        sha: 'def456',
        size: 1024,
        url: `https://api.github.com/repos/${owner}/${repo}/contents/package.json?ref=${ref}`,
        download_url: `https://raw.githubusercontent.com/${owner}/${repo}/${ref}/package.json`,
        content: Buffer.from(JSON.stringify({
          name: 'mcp-github-extractor',
          version: '1.0.0',
          description: 'MCP GitHub Extractor',
          dependencies: {
            'node-fetch': '^3.3.0'
          }
        }, null, 2)).toString('base64'),
        encoding: 'base64'
      };
    }
    
    // Default empty result
    return [];
  }
  
  /**
   * Generate mock repository data
   */
  async _getMockRepo(owner, repo) {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 200));
    
    return {
      id: 12345678,
      name: repo,
      full_name: `${owner}/${repo}`,
      private: false,
      owner: {
        login: owner,
        id: 87654321,
        avatar_url: `https://github.com/avatars/${owner}`
      },
      html_url: `https://github.com/${owner}/${repo}`,
      description: 'A mock repository for MCP extraction testing',
      fork: false,
      created_at: '2023-05-01T00:00:00Z',
      updated_at: new Date().toISOString(),
      pushed_at: new Date().toISOString(),
      default_branch: 'main',
      language: 'JavaScript',
      stargazers_count: 42,
      forks_count: 13,
      open_issues_count: 5
    };
  }
  
  /**
   * Generate mock commits data
   */
  async _getMockCommits(owner, repo, branch, limit) {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 250));
    
    const commits = [];
    for (let i = 0; i < limit; i++) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      
      commits.push({
        sha: `commit${i}${Date.now().toString(36).substring(5)}`,
        commit: {
          author: {
            name: 'MCP Developer',
            email: 'developer@mcp-framework.com',
            date: date.toISOString()
          },
          message: i === 0 
            ? 'Add MCP support for GitHub extraction' 
            : `Mock commit message ${i}`
        },
        author: {
          login: owner,
          id: 87654321,
          avatar_url: `https://github.com/avatars/${owner}`
        },
        html_url: `https://github.com/${owner}/${repo}/commit/abc${i}`
      });
    }
    
    return commits;
  }
}

/**
 * Extract data from GitHub repository
 */
async function extractFromGitHub(repoPath, branch = 'main', path = '') {
  console.log(`Extracting GitHub repo: ${repoPath}, branch: ${branch}, path: ${path}`);
  
  // 1. Authentication
  const github = new GitHubAPI({ useMock: true }); // Set to false to use real GitHub API
  
  // 2. Parse repository path
  const [owner, repo] = repoPath.split('/');
  if (!owner || !repo) {
    throw new Error('Invalid repository path. Format should be owner/repo');
  }
  
  // 3. Discovery & Extraction
  console.log('Fetching repository information...');
  const [repoInfo, contents, commits] = await Promise.all([
    github.getRepo(owner, repo),
    github.getContents(owner, repo, path, branch),
    github.getCommits(owner, repo, branch, 5)
  ]);
  
  // Parse file content if a single file is requested
  let fileContent = null;
  if (!Array.isArray(contents) && contents.content && contents.encoding === 'base64') {
    fileContent = Buffer.from(contents.content, 'base64').toString('utf-8');
  }
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: `github-${owner}-${repo}-${branch}-${path.replace(/\//g, '-')}-${Date.now()}`,
    operation: "extract",
    parameters: {
      source: "github",
      owner,
      repo,
      branch,
      path
    },
    result: {
      repository: {
        id: repoInfo.id,
        name: repoInfo.name,
        full_name: repoInfo.full_name,
        description: repoInfo.description,
        default_branch: repoInfo.default_branch,
        created_at: repoInfo.created_at,
        updated_at: repoInfo.updated_at,
        language: repoInfo.language,
        stars: repoInfo.stargazers_count,
        forks: repoInfo.forks_count
      },
      contents: Array.isArray(contents) 
        ? contents.map(item => ({
            name: item.name,
            path: item.path,
            type: item.type,
            size: item.size,
            url: item.html_url || item.url
          })) 
        : {
            name: contents.name,
            path: contents.path,
            type: contents.type,
            size: contents.size,
            content: fileContent
          },
      recent_commits: commits.map(commit => ({
        sha: commit.sha,
        message: commit.commit.message,
        author: commit.commit.author.name,
        date: commit.commit.author.date,
        url: commit.html_url
      }))
    },
    metadata: {
      extractionTime: new Date().toISOString(),
      api_version: "v3"
    }
  };
  
  console.log("Generated MCP context:", JSON.stringify(mcpContext, null, 2));
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}

/**
 * Send context to MCP endpoint
 */
async function sendToMcpEndpoint(mcpContext) {
  console.log(`Sending to MCP endpoint: ${MCP_ENDPOINT}`);
  
  const requestBody = {
    modelId: 'github-extractor',
    context: mcpContext
  };
  
  try {
    const response = await fetch(MCP_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
      },
      body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
      throw new Error(`MCP endpoint error: ${response.status}`);
    }
    
    const result = await response.json();
    console.log("MCP Response:", JSON.stringify(result, null, 2));
    return result;
  } catch (error) {
    console.error("Error sending to MCP endpoint:", error.message);
    throw error;
  }
}

/**
 * Main execution
 */
async function main() {
  try {
    // Example: Extract repository information
    const result = await extractFromGitHub('mcp-framework/github-extractor');
    console.log("GitHub extraction complete!");
    
    // Uncomment to extract a specific file
    // const fileResult = await extractFromGitHub('mcp-framework/github-extractor', 'main', 'package.json');
    // console.log("File extraction complete!");
  } catch (error) {
    console.error("Extraction failed:", error);
  }
}

// Run the extractor only if executed directly
if (require.main === module) {
  main();
}

// Export for use in the orchestrator
module.exports = {
  extractFromGitHub,
  sendToMcpEndpoint,
  GitHubAPI
}; 