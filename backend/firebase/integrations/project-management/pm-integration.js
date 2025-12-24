/**
 * Project Management Integration System
 * Supports integration with Jira, Trello, Asana, and other PM tools
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');

class ProjectManagementIntegration {
  constructor() {
    this.config = this.loadConfig();
    this.integrations = {};
    this.eventListeners = {};
  }

  /**
   * Load configuration from environment or config file
   */
  loadConfig() {
    const configPath = path.join(__dirname, '..', '..', 'config', 'pm-integration.json');

    if (fs.existsSync(configPath)) {
      return JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }

    // Default configuration
    return {
      jira: {
        enabled: false,
        baseUrl: process.env.JIRA_BASE_URL,
        username: process.env.JIRA_USERNAME,
        apiToken: process.env.JIRA_API_TOKEN,
        projectKey: process.env.JIRA_PROJECT_KEY
      },
      trello: {
        enabled: false,
        apiKey: process.env.TRELLO_API_KEY,
        apiToken: process.env.TRELLO_API_TOKEN,
        boardId: process.env.TRELLO_BOARD_ID
      },
      asana: {
        enabled: false,
        accessToken: process.env.ASANA_ACCESS_TOKEN,
        workspaceId: process.env.ASANA_WORKSPACE_ID,
        projectId: process.env.ASANA_PROJECT_ID
      }
    };
  }

  /**
   * Initialize integrations based on configuration
   */
  async initialize() {
    console.log('🚀 Initializing Project Management Integrations...');

    if (this.config.jira.enabled) {
      this.integrations.jira = new JiraIntegration(this.config.jira);
      await this.integrations.jira.initialize();
      console.log('✅ Jira integration initialized');
    }

    if (this.config.trello.enabled) {
      this.integrations.trello = new TrelloIntegration(this.config.trello);
      await this.integrations.trello.initialize();
      console.log('✅ Trello integration initialized');
    }

    if (this.config.asana.enabled) {
      this.integrations.asana = new AsanaIntegration(this.config.asana);
      await this.integrations.asana.initialize();
      console.log('✅ Asana integration initialized');
    }

    // Set up webhooks and event listeners
    await this.setupWebhooks();
    console.log('✅ Webhooks and event listeners configured');
  }

  /**
   * Set up webhooks for real-time synchronization
   */
  async setupWebhooks() {
    // Set up webhook endpoints for each integration
    for (const [tool, integration] of Object.entries(this.integrations)) {
      if (integration.setupWebhooks) {
        await integration.setupWebhooks();
      }
    }
  }

  /**
   * Sync documentation tasks with project management tool
   */
  async syncTasks(tasks) {
    const results = {};

    for (const [tool, integration] of Object.entries(this.integrations)) {
      try {
        results[tool] = await integration.syncTasks(tasks);
        console.log(`✅ Synced ${tasks.length} tasks with ${tool}`);
      } catch (error) {
        console.error(`❌ Failed to sync with ${tool}:`, error.message);
        results[tool] = { error: error.message };
      }
    }

    return results;
  }

  /**
   * Create a new task/issue in project management tool
   */
  async createTask(taskData) {
    const results = {};

    for (const [tool, integration] of Object.entries(this.integrations)) {
      try {
        results[tool] = await integration.createTask(taskData);
        console.log(`✅ Created task in ${tool}: ${results[tool].id}`);
      } catch (error) {
        console.error(`❌ Failed to create task in ${tool}:`, error.message);
        results[tool] = { error: error.message };
      }
    }

    return results;
  }

  /**
   * Update task status in project management tool
   */
  async updateTaskStatus(taskId, status, tool = 'all') {
    if (tool === 'all') {
      const results = {};
      for (const [toolName, integration] of Object.entries(this.integrations)) {
        try {
          results[toolName] = await integration.updateTaskStatus(taskId, status);
        } catch (error) {
          results[toolName] = { error: error.message };
        }
      }
      return results;
    }

    if (!this.integrations[tool]) {
      throw new Error(`Integration not found: ${tool}`);
    }

    return await this.integrations[tool].updateTaskStatus(taskId, status);
  }

  /**
   * Get project status and metrics
   */
  async getProjectStatus() {
    const status = {
      tasks: {},
      burndown: {},
      velocity: {},
      blockers: []
    };

    for (const [tool, integration] of Object.entries(this.integrations)) {
      try {
        const toolStatus = await integration.getProjectStatus();
        status.tasks[tool] = toolStatus.tasks;
        status.burndown[tool] = toolStatus.burndown;
        status.velocity[tool] = toolStatus.velocity;
        status.blockers.push(...toolStatus.blockers);
      } catch (error) {
        console.error(`❌ Failed to get status from ${tool}:`, error.message);
      }
    }

    return status;
  }

  /**
   * Generate reports for project management
   */
  async generateReports() {
    const reports = {
      taskCompletion: {},
      burndown: {},
      velocity: {},
      blockers: {},
      recommendations: []
    };

    for (const [tool, integration] of Object.entries(this.integrations)) {
      try {
        const report = await integration.generateReport();
        Object.assign(reports, report);
      } catch (error) {
        console.error(`❌ Failed to generate report for ${tool}:`, error.message);
      }
    }

    return reports;
  }

  /**
   * Handle incoming webhooks from project management tools
   */
  async handleWebhook(tool, eventType, data) {
    console.log(`🎣 Received ${eventType} webhook from ${tool}`);

    // Emit event to registered listeners
    if (this.eventListeners[tool] && this.eventListeners[tool][eventType]) {
      for (const listener of this.eventListeners[tool][eventType]) {
        try {
          await listener(data);
        } catch (error) {
          console.error(`❌ Webhook listener error:`, error.message);
        }
      }
    }

    // Handle specific event types
    switch (eventType) {
      case 'task_created':
        await this.handleTaskCreated(tool, data);
        break;
      case 'task_updated':
        await this.handleTaskUpdated(tool, data);
        break;
      case 'task_completed':
        await this.handleTaskCompleted(tool, data);
        break;
      default:
        console.log(`ℹ️  Unhandled webhook event: ${eventType}`);
    }
  }

  /**
   * Register event listener for webhooks
   */
  on(tool, eventType, listener) {
    if (!this.eventListeners[tool]) {
      this.eventListeners[tool] = {};
    }
    if (!this.eventListeners[tool][eventType]) {
      this.eventListeners[tool][eventType] = [];
    }
    this.eventListeners[tool][eventType].push(listener);
  }

  // Event handlers
  async handleTaskCreated(tool, data) {
    console.log(`📝 New task created in ${tool}: ${data.title}`);
    // Could trigger documentation updates, notifications, etc.
  }

  async handleTaskUpdated(tool, data) {
    console.log(`🔄 Task updated in ${tool}: ${data.title} - ${data.status}`);
    // Could update local task status, trigger reviews, etc.
  }

  async handleTaskCompleted(tool, data) {
    console.log(`✅ Task completed in ${tool}: ${data.title}`);
    // Could trigger deployment, documentation updates, etc.
  }
}

// Tool-specific integration classes
class JiraIntegration {
  constructor(config) {
    this.config = config;
    this.baseUrl = config.baseUrl;
    this.auth = {
      username: config.username,
      password: config.apiToken
    };
  }

  async initialize() {
    // Test connection
    try {
      await axios.get(`${this.baseUrl}/rest/api/2/myself`, {
        auth: this.auth
      });
    } catch (error) {
      throw new Error(`Failed to connect to Jira: ${error.message}`);
    }
  }

  async syncTasks(tasks) {
    const results = [];

    for (const task of tasks) {
      try {
        const jiraIssue = await this.createOrUpdateIssue(task);
        results.push({
          localId: task.id,
          jiraId: jiraIssue.key,
          status: 'synced'
        });
      } catch (error) {
        results.push({
          localId: task.id,
          error: error.message,
          status: 'failed'
        });
      }
    }

    return results;
  }

  async createTask(taskData) {
    const issueData = {
      fields: {
        project: { key: this.config.projectKey },
        summary: taskData.title,
        description: taskData.description,
        issuetype: { name: 'Task' },
        priority: { name: this.mapPriority(taskData.priority) },
        labels: ['documentation', 'automated']
      }
    };

    const response = await axios.post(
      `${this.baseUrl}/rest/api/2/issue`,
      issueData,
      { auth: this.auth }
    );

    return {
      id: response.data.key,
      url: `${this.baseUrl}/browse/${response.data.key}`
    };
  }

  async updateTaskStatus(taskId, status) {
    const statusId = this.mapStatus(status);

    await axios.post(
      `${this.baseUrl}/rest/api/2/issue/${taskId}/transitions`,
      { transition: { id: statusId } },
      { auth: this.auth }
    );

    return { status: 'updated' };
  }

  async getProjectStatus() {
    const response = await axios.get(
      `${this.baseUrl}/rest/api/2/search?jql=project=${this.config.projectKey}`,
      { auth: this.auth }
    );

    return {
      tasks: response.data.issues.map(issue => ({
        id: issue.key,
        title: issue.fields.summary,
        status: issue.fields.status.name,
        priority: issue.fields.priority.name
      })),
      burndown: this.calculateBurndown(response.data.issues),
      velocity: this.calculateVelocity(response.data.issues),
      blockers: response.data.issues
        .filter(issue => issue.fields.status.name === 'Blocked')
        .map(issue => ({
          id: issue.key,
          title: issue.fields.summary,
          blocker: issue.fields.customfield_blocker || 'Unknown blocker'
        }))
    };
  }

  mapPriority(priority) {
    const mapping = {
      'low': 'Low',
      'medium': 'Medium',
      'high': 'High',
      'critical': 'Highest'
    };
    return mapping[priority] || 'Medium';
  }

  mapStatus(status) {
    const mapping = {
      'todo': '11',      // To Do
      'in_progress': '21', // In Progress
      'review': '31',   // In Review
      'done': '41'      // Done
    };
    return mapping[status] || '11';
  }

  calculateBurndown(issues) {
    // Simplified burndown calculation
    const total = issues.length;
    const completed = issues.filter(issue =>
      issue.fields.status.name === 'Done'
    ).length;

    return {
      total,
      completed,
      remaining: total - completed,
      completionRate: (completed / total) * 100
    };
  }

  calculateVelocity(issues) {
    // Calculate completed issues in recent sprints
    const recentCompleted = issues.filter(issue =>
      issue.fields.status.name === 'Done' &&
      new Date(issue.fields.updated) > new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
    );

    return {
      completedLast30Days: recentCompleted.length,
      averagePerWeek: recentCompleted.length / 4
    };
  }
}

class TrelloIntegration {
  constructor(config) {
    this.config = config;
    this.apiKey = config.apiKey;
    this.apiToken = config.apiToken;
    this.boardId = config.boardId;
  }

  async initialize() {
    try {
      await axios.get(`https://api.trello.com/1/boards/${this.boardId}`, {
        params: {
          key: this.apiKey,
          token: this.apiToken
        }
      });
    } catch (error) {
      throw new Error(`Failed to connect to Trello: ${error.message}`);
    }
  }

  async createTask(taskData) {
    const response = await axios.post(
      `https://api.trello.com/1/cards`,
      null,
      {
        params: {
          key: this.apiKey,
          token: this.apiToken,
          idList: await this.getTodoListId(),
          name: taskData.title,
          desc: taskData.description,
          pos: 'top'
        }
      }
    );

    return {
      id: response.data.id,
      url: response.data.url
    };
  }

  async getTodoListId() {
    const response = await axios.get(
      `https://api.trello.com/1/boards/${this.boardId}/lists`,
      {
        params: {
          key: this.apiKey,
          token: this.apiToken
        }
      }
    );

    const todoList = response.data.find(list => list.name === 'To Do');
    if (!todoList) {
      throw new Error('Could not find "To Do" list in Trello board');
    }

    return todoList.id;
  }
}

class AsanaIntegration {
  constructor(config) {
    this.config = config;
    this.accessToken = config.accessToken;
    this.workspaceId = config.workspaceId;
    this.projectId = config.projectId;
  }

  async initialize() {
    try {
      await axios.get('https://app.asana.com/api/1.0/users/me', {
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      });
    } catch (error) {
      throw new Error(`Failed to connect to Asana: ${error.message}`);
    }
  }

  async createTask(taskData) {
    const response = await axios.post(
      'https://app.asana.com/api/1.0/tasks',
      {
        data: {
          name: taskData.title,
          notes: taskData.description,
          projects: [this.projectId],
          workspace: this.workspaceId
        }
      },
      {
        headers: {
          'Authorization': `Bearer ${this.accessToken}`
        }
      }
    );

    return {
      id: response.data.data.gid,
      url: `https://app.asana.com/0/${this.projectId}/${response.data.data.gid}`
    };
  }
}

module.exports = ProjectManagementIntegration;
