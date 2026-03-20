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
export type GitHubToolName = 'list_issues' | 'create_issue' | 'update_issue' | 'list_prs' | 'create_pr' | 'get_repo_info' | 'list_branches';
/**
 * Tool arguments for each GitHub tool
 */
export interface GitHubToolArguments {
    list_issues: {
        state?: 'open' | 'closed' | 'all';
        labels?: string[];
        page?: number;
    };
    create_issue: {
        title: string;
        body: string;
        labels?: string[];
    };
    update_issue: {
        issue_number: number;
        title?: string;
        body?: string;
        state?: 'open' | 'closed';
    };
    list_prs: {
        state?: 'open' | 'closed' | 'all';
        page?: number;
    };
    create_pr: {
        title: string;
        body: string;
        head: string;
        base: string;
    };
    get_repo_info: {};
    list_branches: {};
}
/**
 * MCP Connector for GitHub API
 * Provides issue tracking, PR management, and repository operations
 */
export declare class GitHubConnector {
    private octokit;
    private owner;
    private repo;
    constructor(config: GitHubConfig);
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
                    state: {
                        type: string;
                        enum: string[];
                        default: string;
                    };
                    labels: {
                        type: string;
                        items: {
                            type: string;
                        };
                    };
                    page: {
                        type: string;
                        default: number;
                    };
                    title?: undefined;
                    body?: undefined;
                    issue_number?: undefined;
                    head?: undefined;
                    base?: undefined;
                };
                required?: undefined;
            };
        } | {
            name: string;
            description: string;
            inputSchema: {
                type: string;
                properties: {
                    title: {
                        type: string;
                    };
                    body: {
                        type: string;
                    };
                    labels: {
                        type: string;
                        items: {
                            type: string;
                        };
                    };
                    state?: undefined;
                    page?: undefined;
                    issue_number?: undefined;
                    head?: undefined;
                    base?: undefined;
                };
                required: string[];
            };
        } | {
            name: string;
            description: string;
            inputSchema: {
                type: string;
                properties: {
                    issue_number: {
                        type: string;
                    };
                    title: {
                        type: string;
                    };
                    body: {
                        type: string;
                    };
                    state: {
                        type: string;
                        enum: string[];
                        default?: undefined;
                    };
                    labels?: undefined;
                    page?: undefined;
                    head?: undefined;
                    base?: undefined;
                };
                required: string[];
            };
        } | {
            name: string;
            description: string;
            inputSchema: {
                type: string;
                properties: {
                    state: {
                        type: string;
                        enum: string[];
                        default: string;
                    };
                    page: {
                        type: string;
                        default: number;
                    };
                    labels?: undefined;
                    title?: undefined;
                    body?: undefined;
                    issue_number?: undefined;
                    head?: undefined;
                    base?: undefined;
                };
                required?: undefined;
            };
        } | {
            name: string;
            description: string;
            inputSchema: {
                type: string;
                properties: {
                    title: {
                        type: string;
                    };
                    body: {
                        type: string;
                    };
                    head: {
                        type: string;
                        description: string;
                    };
                    base: {
                        type: string;
                        description: string;
                    };
                    state?: undefined;
                    labels?: undefined;
                    page?: undefined;
                    issue_number?: undefined;
                };
                required: string[];
            };
        } | {
            name: string;
            description: string;
            inputSchema: {
                type: string;
                properties?: undefined;
                required?: undefined;
            };
        })[];
    }>;
    /**
     * Execute a tool by name
     */
    executeTool<T extends GitHubToolName>(name: T, args: GitHubToolArguments[T]): Promise<any>;
    private listIssues;
    private createIssue;
    private updateIssue;
    private listPRs;
    private createPR;
    private getRepoInfo;
    private listBranches;
}
