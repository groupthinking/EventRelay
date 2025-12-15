// MCP Orchestration Workflows - Durable execution pattern

interface PostgresConnector {
  executeTool(name: string, params: Record<string, unknown>): Promise<{ rows: Record<string, unknown>[] }>;
}

interface GitHubConnector {
  executeTool(name: string, params: Record<string, unknown>): Promise<unknown[]>;
}

interface SlackConnector {
  executeTool(name: string, params: Record<string, unknown>): Promise<void>;
}

interface MCPOrchestrationContext {
  input: {
    githubConnector: GitHubConnector;
    postgresConnector: PostgresConnector;
    slackConnector: SlackConnector;
    labels?: string[];
    slackChannel?: string;
  };
}

interface AgentMonitoringContext {
  input: {
    postgresConnector: PostgresConnector;
    slackConnector: SlackConnector;
  };
}

/**
 * Orchestrate MCP connectors with durable workflows
 * Example: Sync GitHub issues to database and notify Slack
 */
export async function mcpOrchestrationWorkflow(context: MCPOrchestrationContext) {
  // Step 1: Fetch GitHub issues
  const issues = await context.input.githubConnector.executeTool('list_issues', {
    state: 'open',
    labels: context.input.labels || []
  }) as { number: number; title: string; state: string; created_at: string }[];

  // Step 2: Sync to database
  const postgres = context.input.postgresConnector;
  const queries = issues.map((issue) => ({
    query: `
      INSERT INTO github_issues (issue_number, title, state, created_at)
      VALUES ($1, $2, $3, $4)
      ON CONFLICT (issue_number) DO UPDATE SET
        title = EXCLUDED.title,
        state = EXCLUDED.state
    `,
    params: [issue.number, issue.title, issue.state, issue.created_at]
  }));

  await postgres.executeTool('transaction', { queries });

  // Step 3: Notify Slack
  const slack = context.input.slackConnector;
  await slack.executeTool('send_message', {
    channel: context.input.slackChannel || '#engineering',
    text: `✅ Synced ${issues.length} GitHub issues to database`
  });

  return {
    success: true,
    issuesSynced: issues.length,
    completedAt: new Date().toISOString()
  };
}

/**
 * Long-running agent workflow example
 * Demonstrates periodic execution and error recovery
 */
export async function agentMonitoringWorkflow(context: AgentMonitoringContext) {
  const postgres = context.input.postgresConnector;

  // Check database health
  const result = await postgres.executeTool('query', {
    query: 'SELECT COUNT(*) as active_connections FROM pg_stat_activity'
  });

  const dbConnections = result.rows[0]?.active_connections as number;
  const healthy = dbConnections < 100;

  if (!healthy) {
    const slack = context.input.slackConnector;
    await slack.executeTool('send_message', {
      channel: '#alerts',
      text: `🚨 System health alert: ${dbConnections} active database connections`
    });
    return { alerted: true, reason: 'high_db_connections' };
  }

  return { alerted: false, status: 'healthy' };
}

/**
 * Execute MCP orchestration workflow
 */
export async function runMCPOrchestration(config: {
  githubConnector: GitHubConnector;
  postgresConnector: PostgresConnector;
  slackConnector: SlackConnector;
  labels?: string[];
  slackChannel?: string;
}) {
  return await mcpOrchestrationWorkflow({ input: config });
}

/**
 * Execute agent monitoring workflow
 */
export async function runAgentMonitoring(config: {
  postgresConnector: PostgresConnector;
  slackConnector: SlackConnector;
}) {
  return await agentMonitoringWorkflow({ input: config });
}
