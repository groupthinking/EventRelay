#!/usr/bin/env node

/**
 * Project Management Integration CLI
 * Command-line interface for managing PM tool integrations
 */

const ProjectManagementIntegration = require('./pm-integration');
const WebhookServer = require('./webhook-server');
const fs = require('fs');
const path = require('path');

class PMCLI {
  constructor() {
    this.pmIntegration = new ProjectManagementIntegration();
    this.webhookServer = null;
  }

  async run() {
    const command = process.argv[2];
    const args = process.argv.slice(3);

    try {
      switch (command) {
        case 'init':
          await this.initialize();
          break;
        case 'sync':
          await this.syncTasks(args);
          break;
        case 'create':
          await this.createTask(args);
          break;
        case 'status':
          await this.showStatus();
          break;
        case 'webhook':
          await this.handleWebhookCommand(args);
          break;
        case 'config':
          await this.showConfig();
          break;
        case 'test':
          await this.testConnection(args);
          break;
        default:
          this.showHelp();
      }
    } catch (error) {
      console.error('❌ Error:', error.message);
      process.exit(1);
    }
  }

  async initialize() {
    console.log('🚀 Initializing Project Management Integration...');

    try {
      await this.pmIntegration.initialize();
      console.log('✅ Project Management Integration initialized successfully!');
      console.log('');
      console.log('📋 Next steps:');
      console.log('1. Configure your PM tool credentials in config/pm-integration.json');
      console.log('2. Run: npm run pm:test <tool> to test the connection');
      console.log('3. Run: npm run pm:sync to synchronize existing tasks');
      console.log('4. Run: npm run pm:webhook start to start the webhook server');
    } catch (error) {
      console.error('❌ Initialization failed:', error.message);
      console.log('');
      console.log('🔧 Troubleshooting:');
      console.log('1. Check your configuration in config/pm-integration.json');
      console.log('2. Verify your API credentials are correct');
      console.log('3. Ensure the PM tool is accessible from your network');
      console.log('4. Check the error message above for specific details');
      process.exit(1);
    }
  }

  async syncTasks(args) {
    const tool = args[0] || 'all';
    console.log(`🔄 Synchronizing tasks with ${tool}...`);

    // Get tasks from local documentation system
    const tasks = await this.getLocalTasks();

    if (tasks.length === 0) {
      console.log('ℹ️  No tasks found to synchronize');
      return;
    }

    const results = await this.pmIntegration.syncTasks(tasks);

    console.log('📊 Synchronization Results:');
    Object.entries(results).forEach(([toolName, toolResults]) => {
      console.log(`\n🔧 ${toolName.toUpperCase()}:`);
      toolResults.forEach(result => {
        if (result.error) {
          console.log(`  ❌ ${result.localId}: ${result.error}`);
        } else {
          console.log(`  ✅ ${result.localId} → ${result.jiraId || result.id}`);
        }
      });
    });
  }

  async createTask(args) {
    const title = args.join(' ');

    if (!title) {
      console.error('❌ Error: Please provide a task title');
      console.log('Usage: npm run pm:create <task title>');
      process.exit(1);
    }

    console.log(`📝 Creating task: "${title}"`);

    const taskData = {
      title,
      description: `Task created via PM Integration CLI on ${new Date().toISOString()}`,
      priority: 'medium',
      labels: ['documentation', 'cli-created']
    };

    const results = await this.pmIntegration.createTask(taskData);

    console.log('📊 Task Creation Results:');
    Object.entries(results).forEach(([toolName, result]) => {
      if (result.error) {
        console.log(`  ❌ ${toolName}: ${result.error}`);
      } else {
        console.log(`  ✅ ${toolName}: ${result.url || result.id}`);
      }
    });
  }

  async showStatus() {
    console.log('📊 Project Management Integration Status\n');

    const config = this.pmIntegration.config;

    console.log('🔧 Configured Integrations:');
    Object.entries(config.integrations || {}).forEach(([tool, settings]) => {
      const status = settings.enabled ? '✅ Enabled' : '❌ Disabled';
      console.log(`  ${tool}: ${status}`);
    });

    console.log('\n📈 Project Status:');
    try {
      const status = await this.pmIntegration.getProjectStatus();

      Object.entries(status.tasks).forEach(([tool, tasks]) => {
        console.log(`\n🔧 ${tool.toUpperCase()}:`);
        const byStatus = tasks.reduce((acc, task) => {
          acc[task.status] = (acc[task.status] || 0) + 1;
          return acc;
        }, {});

        Object.entries(byStatus).forEach(([status, count]) => {
          console.log(`  ${status}: ${count} tasks`);
        });
      });

      if (status.blockers.length > 0) {
        console.log('\n🚨 Active Blockers:');
        status.blockers.slice(0, 5).forEach(blocker => {
          console.log(`  • ${blocker.title} (${blocker.id})`);
        });
      }
    } catch (error) {
      console.log('  ❌ Unable to retrieve project status');
    }
  }

  async handleWebhookCommand(args) {
    const subCommand = args[0];

    switch (subCommand) {
      case 'start':
        await this.startWebhookServer();
        break;
      case 'stop':
        await this.stopWebhookServer();
        break;
      case 'status':
        this.showWebhookStatus();
        break;
      default:
        console.log('Webhook commands:');
        console.log('  start  - Start the webhook server');
        console.log('  stop   - Stop the webhook server');
        console.log('  status - Show webhook server status');
    }
  }

  async startWebhookServer() {
    if (this.webhookServer) {
      console.log('ℹ️  Webhook server is already running');
      return;
    }

    console.log('🚀 Starting webhook server...');
    this.webhookServer = new WebhookServer(this.pmIntegration);

    try {
      await this.webhookServer.start();
      console.log('✅ Webhook server started successfully!');
      console.log('📡 Configure your PM tool webhooks to point to:');
      console.log(`   ${this.pmIntegration.config.webhooks.baseUrl}:${this.pmIntegration.config.webhooks.port}/webhooks/<tool>`);

      // Keep the process running
      process.on('SIGINT', async () => {
        console.log('\n🛑 Shutting down webhook server...');
        await this.webhookServer.stop();
        process.exit(0);
      });

      // Keep alive
      setInterval(() => {}, 1000);
    } catch (error) {
      console.error('❌ Failed to start webhook server:', error.message);
      process.exit(1);
    }
  }

  async stopWebhookServer() {
    if (!this.webhookServer) {
      console.log('ℹ️  Webhook server is not running');
      return;
    }

    await this.webhookServer.stop();
    this.webhookServer = null;
    console.log('✅ Webhook server stopped');
  }

  showWebhookStatus() {
    if (!this.webhookServer) {
      console.log('❌ Webhook server is not running');
      return;
    }

    const status = this.webhookServer.getHealthStatus();
    console.log('📊 Webhook Server Status:');
    console.log(`  Status: ${status.status}`);
    console.log(`  Uptime: ${Math.floor(status.uptime)} seconds`);
    console.log(`  Port: ${status.config.port}`);
    console.log(`  SSL: ${status.config.ssl ? 'Enabled' : 'Disabled'}`);
    console.log(`  Rate Limit: ${status.config.rateLimit.maxRequests} requests per ${status.config.rateLimit.windowMs / 1000} seconds`);
  }

  async showConfig() {
    console.log('⚙️  Project Management Integration Configuration\n');

    const config = this.pmIntegration.config;

    Object.entries(config.integrations || {}).forEach(([tool, settings]) => {
      console.log(`🔧 ${tool.toUpperCase()}:`);
      console.log(`  Enabled: ${settings.enabled ? '✅' : '❌'}`);

      if (settings.enabled) {
        // Show masked credentials
        Object.entries(settings).forEach(([key, value]) => {
          if (key.includes('token') || key.includes('password') || key.includes('secret')) {
            console.log(`  ${key}: ${value ? '********' : 'Not set'}`);
          } else if (key !== 'enabled') {
            console.log(`  ${key}: ${value}`);
          }
        });
      }
      console.log('');
    });

    console.log('🔄 Sync Configuration:');
    console.log(`  Enabled: ${config.sync.enabled ? '✅' : '❌'}`);
    console.log(`  Interval: ${config.sync.interval / 1000} seconds`);
    console.log(`  Batch Size: ${config.sync.batchSize}`);

    console.log('\n📡 Webhook Configuration:');
    console.log(`  Enabled: ${config.webhooks.enabled ? '✅' : '❌'}`);
    console.log(`  Base URL: ${config.webhooks.baseUrl}`);
    console.log(`  Port: ${config.webhooks.port}`);
    console.log(`  SSL: ${config.webhooks.ssl ? '✅' : '❌'}`);
  }

  async testConnection(args) {
    const tool = args[0];

    if (!tool) {
      console.error('❌ Error: Please specify a tool to test');
      console.log('Usage: npm run pm:test <tool>');
      console.log('Available tools: jira, trello, asana');
      process.exit(1);
    }

    console.log(`🔍 Testing ${tool} connection...`);

    if (!this.pmIntegration.integrations[tool]) {
      console.error(`❌ Error: ${tool} integration is not configured or disabled`);
      console.log('Check your configuration in config/pm-integration.json');
      process.exit(1);
    }

    try {
      // Test the connection (this would need to be implemented in each integration)
      const testResult = await this.pmIntegration.integrations[tool].testConnection();
      console.log('✅ Connection test successful!');
      console.log(`  Status: ${testResult.status}`);
      console.log(`  User: ${testResult.user || 'N/A'}`);
      console.log(`  Projects: ${testResult.projects || 'N/A'}`);
    } catch (error) {
      console.error('❌ Connection test failed:', error.message);
      console.log('');
      console.log('🔧 Troubleshooting steps:');
      console.log('1. Verify your API credentials in config/pm-integration.json');
      console.log('2. Check network connectivity to the PM tool');
      console.log('3. Ensure the PM tool instance is accessible');
      console.log('4. Verify API permissions and scopes');
      process.exit(1);
    }
  }

  async getLocalTasks() {
    // This would integrate with your local task management system
    // For now, return a sample set of tasks
    return [
      {
        id: 'task-001',
        title: 'Update API documentation',
        description: 'Update API docs with new endpoints',
        status: 'todo',
        priority: 'medium'
      },
      {
        id: 'task-002',
        title: 'Fix authentication bug',
        description: 'JWT token expiration issue',
        status: 'in_progress',
        priority: 'high'
      }
    ];
  }

  showHelp() {
    console.log('🤖 Project Management Integration CLI\n');
    console.log('Usage: npm run pm:<command> [options]\n');
    console.log('Commands:');
    console.log('  init           Initialize PM integration');
    console.log('  sync [tool]    Sync tasks with PM tools');
    console.log('  create <title> Create a new task');
    console.log('  status         Show integration status');
    console.log('  webhook        Manage webhook server');
    console.log('  config         Show current configuration');
    console.log('  test <tool>    Test connection to PM tool');
    console.log('');
    console.log('Examples:');
    console.log('  npm run pm:init');
    console.log('  npm run pm:create "Fix login bug"');
    console.log('  npm run pm:sync jira');
    console.log('  npm run pm:webhook start');
    console.log('  npm run pm:test jira');
    console.log('');
    console.log('For more help, run: npm run pm:help');
  }
}

// Run CLI if called directly
if (require.main === module) {
  const cli = new PMCLI();
  cli.run().catch(error => {
    console.error('CLI Error:', error.message);
    process.exit(1);
  });
}

module.exports = PMCLI;
