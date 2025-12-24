#!/usr/bin/env node

/**
 * GitLab Webhook Setup Script
 * Helps configure GitLab webhooks to integrate with Firebase system
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');

class GitLabWebhookSetup {
  constructor() {
    this.config = this.loadConfig();
  }

  loadConfig() {
    const configPath = path.join(__dirname, '..', 'config', 'pm-integration.json');
    if (fs.existsSync(configPath)) {
      return JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }
    return {};
  }

  /**
   * Setup GitLab webhooks
   */
  async setupWebhooks(options = {}) {
    console.log('🔗 Setting up GitLab webhooks...');

    // Extract GitLab info from git config
    const gitlabInfo = await this.getGitLabInfo();
    console.log(`📍 Detected GitLab instance: ${gitlabInfo.instance}`);
    console.log(`📁 Project path: ${gitlabInfo.projectPath}`);

    const gitlabConfig = this.config.webhooks?.gitlab;
    if (!gitlabConfig) {
      console.error('❌ GitLab configuration not found. Please configure webhooks in pm-integration.json');
      return;
    }

    const baseUrl = this.config.webhooks.baseUrl;
    const projectId = options.projectId || await this.getProjectId(gitlabInfo);
    const webhookUrl = `${baseUrl}/webhooks/gitlab`;

    console.log(`📡 Webhook URL: ${webhookUrl}`);
    console.log(`🆔 Project ID: ${projectId}`);

    // Try to create webhook via API
    const apiCreated = await this.createWebhookViaAPI(gitlabInfo, projectId, webhookUrl, gitlabConfig);

    if (apiCreated) {
      console.log('\n✅ Webhook created successfully via GitLab API!');
      return { apiCreated: true, projectId, webhookUrl };
    }

    // Fallback to manual configuration
    console.log('\n⚠️  API creation failed. Providing manual setup instructions...');
    const webhookConfig = this.generateManualConfig(webhookUrl, gitlabConfig);
    this.generateManualInstructions(webhookUrl, webhookConfig);
    this.generateTestCommands(webhookUrl, gitlabConfig.webhookToken);

    return { apiCreated: false, projectId, webhookUrl, config: webhookConfig };
  }

  /**
   * Get GitLab instance info from git config
   */
  async getGitLabInfo() {
    try {
      const { execSync } = require('child_process');
      const remoteUrl = execSync('git config --get remote.origin.url', { encoding: 'utf8' }).trim();

      // Parse GitLab URL
      const urlMatch = remoteUrl.match(/git@([^:]+):(.+)\.git/);
      if (urlMatch) {
        return {
          instance: `https://${urlMatch[1]}`,
          projectPath: urlMatch[2]
        };
      }

      // Handle HTTPS URLs
      const httpsMatch = remoteUrl.match(/https:\/\/([^\/]+)\/(.+)\.git/);
      if (httpsMatch) {
        return {
          instance: `https://${httpsMatch[1]}`,
          projectPath: httpsMatch[2]
        };
      }

      throw new Error('Could not parse GitLab URL');
    } catch (error) {
      console.warn('⚠️  Could not detect GitLab info from git config:', error.message);
      return {
        instance: 'https://gitlab.com',
        projectPath: 'groupthinking/firebase'
      };
    }
  }

  /**
   * Get project ID from GitLab API
   */
  async getProjectId(gitlabInfo) {
    try {
      const token = process.env.GITLAB_API_TOKEN;
      if (!token) {
        console.warn('⚠️  No GITLAB_API_TOKEN found. Using project path as fallback.');
        return encodeURIComponent(gitlabInfo.projectPath);
      }

      const response = await axios.get(
        `${gitlabInfo.instance}/api/v4/projects/${encodeURIComponent(gitlabInfo.projectPath)}`,
        {
          headers: { 'PRIVATE-TOKEN': token }
        }
      );

      return response.data.id;
    } catch (error) {
      console.warn('⚠️  Could not get project ID via API:', error.message);
      return encodeURIComponent(gitlabInfo.projectPath);
    }
  }

  /**
   * Create webhook via GitLab API
   */
  async createWebhookViaAPI(gitlabInfo, projectId, webhookUrl, gitlabConfig) {
    try {
      const token = process.env.GITLAB_API_TOKEN;
      if (!token) {
        console.warn('⚠️  No GITLAB_API_TOKEN found. Skipping API creation.');
        return false;
      }

      console.log('🔧 Creating webhook via GitLab API...');

      const webhookData = {
        url: webhookUrl,
        token: gitlabConfig.webhookToken,
        enable_ssl_verification: true,
        push_events: true,
        merge_requests_events: true,
        pipeline_events: true,
        job_events: true,
        tag_push_events: true,
        note_events: true,
        confidential_issues_events: false,
        confidential_note_events: false,
        wiki_page_events: false,
        deployment_events: false,
        releases_events: false,
        issues_events: false
      };

      console.log(`📡 POST ${gitlabInfo.instance}/api/v4/projects/${projectId}/hooks`);
      console.log(`🔗 Webhook URL: ${webhookUrl}`);

      const response = await axios.post(
        `${gitlabInfo.instance}/api/v4/projects/${projectId}/hooks`,
        webhookData,
        {
          headers: {
            'PRIVATE-TOKEN': token,
            'Content-Type': 'application/json'
          },
          timeout: 10000
        }
      );

      if (response.status === 201) {
        console.log(`✅ SUCCESS: Webhook created with ID: ${response.data.id}`);
        console.log(`📋 Webhook URL: ${response.data.url}`);
        console.log(`🔄 Active events: ${Object.keys(response.data).filter(key => key.endsWith('_events') && response.data[key]).join(', ')}`);
        return true;
      }
    } catch (error) {
      console.error('❌ Failed to create webhook via API:', error.response?.data || error.message);

      if (error.response?.status === 401) {
        console.log('\n🔐 Authentication failed. Please check your GITLAB_API_TOKEN');
      } else if (error.response?.status === 403) {
        console.log('\n🚫 Permission denied. Make sure your token has "api" scope');
      } else if (error.response?.status === 404) {
        console.log('\n📁 Project not found. Please check the project ID');
      }

      return false;
    }
    return false;
  }

  /**
   * Generate manual webhook configuration
   */
  generateManualConfig(webhookUrl, gitlabConfig) {
    return {
      url: webhookUrl,
      token: gitlabConfig.webhookToken || 'your-webhook-token',
      enable_ssl_verification: true,
      push_events: true,
      merge_requests_events: true,
      pipeline_events: true,
      job_events: true,
      tag_push_events: true,
      note_events: true,
      confidential_issues_events: false,
      confidential_note_events: false,
      wiki_page_events: false,
      deployment_events: false,
      releases_events: false,
      issues_events: false
    };
  }

  /**
   * Generate manual setup instructions
   */
  generateManualInstructions(webhookUrl, webhookConfig) {
    console.log('\n📋 Manual Setup Instructions:');
    console.log('1. Go to https://gitlab.com/groupthinking/firebase');
    console.log('2. Navigate to Settings > Webhooks');
    console.log('3. Click "Add new webhook"');
    console.log(`4. URL: ${webhookUrl}`);
    console.log(`5. Secret token: ${webhookConfig.token}`);
    console.log('6. Select triggers:');
    console.log('   ✅ Push events');
    console.log('   ✅ Merge request events');
    console.log('   ✅ Pipeline events');
    console.log('   ✅ Job events');
    console.log('   ✅ Tag push events');
    console.log('   ✅ Note events');
    console.log('7. Enable SSL verification');
    console.log('8. Click "Add webhook"');
  }

  /**
   * Auto setup webhooks with API token
   */
  async autoSetup() {
    console.log('🚀 Auto-setting up GitLab webhooks...');

    // Check if API token is available
    const token = process.env.GITLAB_API_TOKEN;
    if (!token) {
      console.log('\n❌ No GITLAB_API_TOKEN found in environment variables.');
      console.log('\n📋 To get a GitLab API token:');
      this.showTokenInstructions();
      console.log('\n🔧 After getting your token, run:');
      console.log('   export GITLAB_API_TOKEN="your-token-here"');
      console.log('   npm run gitlab:auto-setup');
      return;
    }

    console.log('✅ Found GitLab API token');

    // Get GitLab info
    const gitlabInfo = await this.getGitLabInfo();
    console.log(`📍 GitLab instance: ${gitlabInfo.instance}`);
    console.log(`📁 Project path: ${gitlabInfo.projectPath}`);

    const baseUrl = this.config.webhooks.baseUrl;
    const webhookUrl = `${baseUrl}/webhooks/gitlab`;
    const projectId = 74110852; // Using the project ID you provided

    console.log(`🎯 Webhook URL: ${webhookUrl}`);
    console.log(`🆔 Project ID: ${projectId}`);

    // Check webhook token
    const webhookToken = this.config.webhooks?.gitlab?.webhookToken;
    if (!webhookToken || webhookToken.includes('your-gitlab-webhook-token')) {
      console.log('\n⚠️  Using configured webhook token from config');
    }

    // Try to create webhook via API
    const apiCreated = await this.createWebhookViaAPI(gitlabInfo, projectId, webhookUrl, this.config.webhooks.gitlab);

    if (apiCreated) {
      console.log('\n🎉 SUCCESS: Webhook created via GitLab API!');
      console.log('📡 Your Firebase system is now connected to GitLab');
      console.log('🔄 Webhooks will trigger on:');
      console.log('   • Code pushes (commits)');
      console.log('   • Pipeline status changes');
      console.log('   • Job completions');
      console.log('   • Merge request updates');
      console.log('   • Release tags');

      console.log('\n🧪 Test your setup:');
      console.log('   npm run gitlab:validate-webhooks');
    } else {
      console.log('\n⚠️  API creation failed. Providing manual setup...');
      const webhookConfig = this.generateManualConfig(webhookUrl, this.config.webhooks.gitlab);
      this.generateManualInstructions(webhookUrl, webhookConfig);
      this.generateTestCommands(webhookUrl, webhookToken);
    }
  }

  /**
   * Generate a secure webhook token
   */
  generateWebhookToken() {
    const crypto = require('crypto');
    return crypto.randomBytes(32).toString('hex');
  }

  /**
   * Show GitLab API token setup instructions
   */
  showTokenInstructions() {
    console.log('\n🔑 GitLab API Token Setup Instructions:');
    console.log('');
    console.log('1. Go to https://gitlab.com/-/profile/personal_access_tokens');
    console.log('2. Click "Create a personal access token"');
    console.log('3. Enter a name: "Firebase Webhook Setup"');
    console.log('4. Select scopes:');
    console.log('   ✅ api (Full access to API)');
    console.log('   ✅ read_repository (Read repository data)');
    console.log('   ✅ write_repository (Modify repository data)');
    console.log('5. Click "Create personal access token"');
    console.log('6. Copy the token immediately (you won\'t see it again)');
    console.log('');
    console.log('📝 Set the token as an environment variable:');
    console.log('   export GITLAB_API_TOKEN="your-token-here"');
    console.log('');
    console.log('Or add it to your .env file:');
    console.log('   GITLAB_API_TOKEN=your-token-here');
    console.log('');
    console.log('🔒 Keep this token secure and never commit it to version control!');
  }

  /**
   * Generate test commands for webhook verification
   */
  generateTestCommands(webhookUrl, token) {
    console.log('\n🧪 Test Commands:');

    const testData = {
      push: {
        "object_kind": "push",
        "ref": "refs/heads/main",
        "checkout_sha": "da1560886d4f094c3e6c9ef40349f7d38b5d27dce",
        "user_name": "Test User",
        "project": {
          "id": 1,
          "name": "Firebase Project",
          "web_url": "https://gitlab.com/groupthinking/firebase"
        },
        "commits": [{
          "id": "da1560886d4f094c3e6c9ef40349f7d38b5d27dce",
          "message": "Test commit for webhook",
          "author": { "name": "Test User", "email": "test@example.com" },
          "url": "https://gitlab.com/groupthinking/firebase/-/commit/da1560886d4f094c3e6c9ef40349f7d38b5d27dce"
        }]
      },
      pipeline: {
        "object_kind": "pipeline",
        "object_attributes": {
          "id": 1,
          "status": "success",
          "ref": "main",
          "sha": "da1560886d4f094c3e6c9ef40349f7d38b5d27dce"
        },
        "project": {
          "id": 1,
          "name": "Firebase Project",
          "web_url": "https://gitlab.com/groupthinking/firebase"
        }
      }
    };

    console.log('\n📤 Test Push Event:');
    console.log(`curl -X POST "${webhookUrl}" \\
  -H "Content-Type: application/json" \\
  -H "X-Gitlab-Event: Push Hook" \\
  ${token ? `-H "X-Gitlab-Token: ${token}" \\` : ''}
  -d '${JSON.stringify(testData.push)}'`);

    console.log('\n🔄 Test Pipeline Event:');
    console.log(`curl -X POST "${webhookUrl}" \\
  -H "Content-Type: application/json" \\
  -H "X-Gitlab-Event: Pipeline Hook" \\
  ${token ? `-H "X-Gitlab-Token: ${token}" \\` : ''}
  -d '${JSON.stringify(testData.pipeline)}'`);
  }

  /**
   * Validate webhook configuration
   */
  async validateWebhook(url, token) {
    console.log('🔍 Validating webhook configuration...');

    try {
      // Test basic connectivity
      const response = await axios.get(url.replace('/webhooks/gitlab', '/health'), {
        timeout: 5000
      });

      if (response.status === 200) {
        console.log('✅ Webhook endpoint is accessible');
      }

      // Test with sample data
      const testData = {
        object_kind: "push",
        ref: "refs/heads/main",
        project: { id: 1, name: "Test Project" }
      };

      const headers = {
        'Content-Type': 'application/json',
        'X-Gitlab-Event': 'Push Hook'
      };

      if (token) {
        headers['X-Gitlab-Token'] = token;
      }

      const webhookResponse = await axios.post(url, testData, {
        headers,
        timeout: 5000
      });

      if (webhookResponse.status === 200) {
        console.log('✅ Webhook test successful');
        return true;
      }

    } catch (error) {
      console.error('❌ Webhook validation failed:', error.message);
      return false;
    }
  }

  /**
   * List configured webhooks
   */
  listWebhooks() {
    console.log('📋 Configured Webhooks:');

    const gitlabConfig = this.config.webhooks?.gitlab;
    if (!gitlabConfig) {
      console.log('❌ No GitLab webhooks configured');
      return;
    }

    const baseUrl = this.config.webhooks.baseUrl;
    const webhookUrl = `${baseUrl}/webhooks/gitlab`;

    console.log('\n🔗 GitLab Webhook:');
    console.log(`   URL: ${webhookUrl}`);
    console.log(`   Token: ${gitlabConfig.webhookToken ? '✅ Configured' : '❌ Not configured'}`);
    console.log(`   Events: ${gitlabConfig.events.join(', ')}`);

    console.log('\n📡 Webhook Endpoints:');
    console.log(`   Push Events: ${webhookUrl} (Push Hook)`);
    console.log(`   Pipeline Events: ${webhookUrl} (Pipeline Hook)`);
    console.log(`   Job Events: ${webhookUrl} (Job Hook)`);
    console.log(`   Merge Request Events: ${webhookUrl} (Merge Request Hook)`);
  }
}

// CLI interface
async function main() {
  const args = process.argv.slice(2);
  const command = args[0];
  const options = {};

  // Parse arguments
  for (let i = 1; i < args.length; i += 2) {
    if (args[i].startsWith('--')) {
      options[args[i].substring(2)] = args[i + 1];
    }
  }

  const setup = new GitLabWebhookSetup();

  try {
    switch (command) {
      case 'setup':
        await setup.setupWebhooks(options);
        break;

      case 'auto':
        await setup.autoSetup();
        break;

      case 'validate':
        const url = options.url || `${setup.config.webhooks?.baseUrl}/webhooks/gitlab`;
        const token = options.token || setup.config.webhooks?.gitlab?.webhookToken;
        await setup.validateWebhook(url, token);
        break;

      case 'list':
        setup.listWebhooks();
        break;

      case 'token':
        setup.showTokenInstructions();
        break;

      default:
        console.log('🔗 GitLab Webhook Setup Tool');
        console.log('');
        console.log('🚀 Quick Start:');
        console.log('  npm run gitlab:setup-webhooks');
        console.log('');
        console.log('📋 Commands:');
        console.log('  setup     Generate webhook configuration and setup instructions');
        console.log('  auto      Attempt automatic webhook creation via GitLab API');
        console.log('  validate  Test webhook connectivity and functionality');
        console.log('  list      Show configured webhooks');
        console.log('  token     Show GitLab API token setup instructions');
        console.log('');
        console.log('🔧 Options:');
        console.log('  --projectId <id>    GitLab project ID');
        console.log('  --url <url>         Webhook URL for validation');
        console.log('  --token <token>     Webhook token for validation');
        console.log('');
        console.log('💡 Examples:');
        console.log('  npm run gitlab:setup-webhooks');
        console.log('  npm run gitlab:validate-webhooks');
        console.log('  node scripts/setup-gitlab-webhooks.js auto');
    }
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main().catch(console.error);
}

module.exports = GitLabWebhookSetup;
