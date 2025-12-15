import { Octokit } from '@octokit/rest';

/**
 * GitHub connector configuration
 */
export interface GitHubConfig {
  token: string;
  owner: string;
  repo: string;
}

/**
 * Available GitHub tool names
 */
export type GitHubToolName =
  | 'list_issues'
  | 'create_issue'
  | 'update_issue'
  | 'list_prs'
  | 'create_pr'
  | 'get_repo_info'
  | 'list_branches';

/**
 * Tool arguments for each GitHub tool
 */
export interface GitHubToolArguments {
  list_issues: { state?: 'open' | 'closed' | 'all'; labels?: string[]; page?: number };
  create_issue: { title: string; body: string; labels?: string[] };
  update_issue: { issue_number: number; title?: string; body?: string; state?: 'open' | 'closed' };
  list_prs: { state?: 'open' | 'closed' | 'all'; page?: number };
  create_pr: { title: string; body: string; head: string; base: string };
  get_repo_info: {};
  list_branches: {};
}

/**
 * MCP Connector for GitHub API
 * Provides issue tracking, PR management, and repository operations
 */
export class GitHubConnector {
  private octokit: Octokit;
  private owner: string;
  private repo: string;

  constructor(config: GitHubConfig) {
    this.octokit = new Octokit({ auth: config.token });
    this.owner = config.owner;
    this.repo = config.repo;
  }

  /**
   * List available tools with their schemas
   */
  async listTools() {
    return {
      tools: [
        {
          name: 'list_issues',
          description: 'List repository issues',
          inputSchema: {
            type: 'object',
            properties: {
              state: { type: 'string', enum: ['open', 'closed', 'all'], default: 'open' },
              labels: { type: 'array', items: { type: 'string' } },
              page: { type: 'number', default: 1 }
            }
          }
        },
        {
          name: 'create_issue',
          description: 'Create a new issue',
          inputSchema: {
            type: 'object',
            properties: {
              title: { type: 'string' },
              body: { type: 'string' },
              labels: { type: 'array', items: { type: 'string' } }
            },
            required: ['title', 'body']
          }
        },
        {
          name: 'update_issue',
          description: 'Update an existing issue',
          inputSchema: {
            type: 'object',
            properties: {
              issue_number: { type: 'number' },
              title: { type: 'string' },
              body: { type: 'string' },
              state: { type: 'string', enum: ['open', 'closed'] }
            },
            required: ['issue_number']
          }
        },
        {
          name: 'list_prs',
          description: 'List pull requests',
          inputSchema: {
            type: 'object',
            properties: {
              state: { type: 'string', enum: ['open', 'closed', 'all'], default: 'open' },
              page: { type: 'number', default: 1 }
            }
          }
        },
        {
          name: 'create_pr',
          description: 'Create a new pull request',
          inputSchema: {
            type: 'object',
            properties: {
              title: { type: 'string' },
              body: { type: 'string' },
              head: { type: 'string', description: 'Branch with changes' },
              base: { type: 'string', description: 'Branch to merge into' }
            },
            required: ['title', 'body', 'head', 'base']
          }
        },
        {
          name: 'get_repo_info',
          description: 'Get repository information',
          inputSchema: { type: 'object' }
        },
        {
          name: 'list_branches',
          description: 'List repository branches',
          inputSchema: { type: 'object' }
        }
      ]
    };
  }

  /**
   * Execute a tool by name
   */
  async executeTool<T extends GitHubToolName>(
    name: T,
    args: GitHubToolArguments[T]
  ): Promise<any> {
    try {
      switch (name) {
        case 'list_issues':
          return await this.listIssues(args as GitHubToolArguments['list_issues']);
        case 'create_issue':
          return await this.createIssue(args as GitHubToolArguments['create_issue']);
        case 'update_issue':
          return await this.updateIssue(args as GitHubToolArguments['update_issue']);
        case 'list_prs':
          return await this.listPRs(args as GitHubToolArguments['list_prs']);
        case 'create_pr':
          return await this.createPR(args as GitHubToolArguments['create_pr']);
        case 'get_repo_info':
          return await this.getRepoInfo();
        case 'list_branches':
          return await this.listBranches();
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error: any) {
      console.error(`Error executing tool ${name}:`, error);
      throw new Error(`GitHub API operation failed: ${error.message}`);
    }
  }

  private async listIssues(args: { state?: 'open' | 'closed' | 'all'; labels?: string[]; page?: number }) {
    const response = await this.octokit.issues.listForRepo({
      owner: this.owner,
      repo: this.repo,
      state: args.state || 'open',
      labels: args.labels?.join(','),
      page: args.page || 1,
      per_page: 30
    });
    return response.data;
  }

  private async createIssue(args: { title: string; body: string; labels?: string[] }) {
    const response = await this.octokit.issues.create({
      owner: this.owner,
      repo: this.repo,
      title: args.title,
      body: args.body,
      labels: args.labels
    });
    return response.data;
  }

  private async updateIssue(args: { issue_number: number; title?: string; body?: string; state?: 'open' | 'closed' }) {
    const response = await this.octokit.issues.update({
      owner: this.owner,
      repo: this.repo,
      issue_number: args.issue_number,
      title: args.title,
      body: args.body,
      state: args.state
    });
    return response.data;
  }

  private async listPRs(args: { state?: 'open' | 'closed' | 'all'; page?: number }) {
    const response = await this.octokit.pulls.list({
      owner: this.owner,
      repo: this.repo,
      state: args.state || 'open',
      page: args.page || 1,
      per_page: 30
    });
    return response.data;
  }

  private async createPR(args: { title: string; body: string; head: string; base: string }) {
    const response = await this.octokit.pulls.create({
      owner: this.owner,
      repo: this.repo,
      title: args.title,
      body: args.body,
      head: args.head,
      base: args.base
    });
    return response.data;
  }

  private async getRepoInfo() {
    const response = await this.octokit.repos.get({
      owner: this.owner,
      repo: this.repo
    });
    return response.data;
  }

  private async listBranches() {
    const response = await this.octokit.repos.listBranches({
      owner: this.owner,
      repo: this.repo
    });
    return response.data;
  }
}
