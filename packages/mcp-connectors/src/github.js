"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.GitHubConnector = void 0;
const rest_1 = require("@octokit/rest");
/**
 * MCP Connector for GitHub API
 * Provides issue tracking, PR management, and repository operations
 */
class GitHubConnector {
    octokit;
    owner;
    repo;
    constructor(config) {
        this.octokit = new rest_1.Octokit({ auth: config.token });
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
    async executeTool(name, args) {
        try {
            switch (name) {
                case 'list_issues':
                    return await this.listIssues(args);
                case 'create_issue':
                    return await this.createIssue(args);
                case 'update_issue':
                    return await this.updateIssue(args);
                case 'list_prs':
                    return await this.listPRs(args);
                case 'create_pr':
                    return await this.createPR(args);
                case 'get_repo_info':
                    return await this.getRepoInfo();
                case 'list_branches':
                    return await this.listBranches();
                default:
                    throw new Error(`Unknown tool: ${name}`);
            }
        }
        catch (error) {
            console.error(`Error executing tool ${name}:`, error);
            throw new Error(`GitHub API operation failed: ${error.message}`);
        }
    }
    async listIssues(args) {
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
    async createIssue(args) {
        const response = await this.octokit.issues.create({
            owner: this.owner,
            repo: this.repo,
            title: args.title,
            body: args.body,
            labels: args.labels
        });
        return response.data;
    }
    async updateIssue(args) {
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
    async listPRs(args) {
        const response = await this.octokit.pulls.list({
            owner: this.owner,
            repo: this.repo,
            state: args.state || 'open',
            page: args.page || 1,
            per_page: 30
        });
        return response.data;
    }
    async createPR(args) {
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
    async getRepoInfo() {
        const response = await this.octokit.repos.get({
            owner: this.owner,
            repo: this.repo
        });
        return response.data;
    }
    async listBranches() {
        const response = await this.octokit.repos.listBranches({
            owner: this.owner,
            repo: this.repo
        });
        return response.data;
    }
}
exports.GitHubConnector = GitHubConnector;
//# sourceMappingURL=github.js.map