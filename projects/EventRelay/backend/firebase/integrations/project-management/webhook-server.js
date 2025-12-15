/**
 * Webhook Server for Project Management Integration
 * Handles real-time synchronization with Jira, Trello, Asana, etc.
 */

const express = require('express');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

class WebhookServer {
  constructor(pmIntegration) {
    this.pmIntegration = pmIntegration;
    this.app = express();
    this.config = this.loadConfig();
    this.setupMiddleware();
    this.setupRoutes();
  }

  loadConfig() {
    const configPath = path.join(__dirname, '..', '..', 'config', 'pm-integration.json');
    return JSON.parse(fs.readFileSync(configPath, 'utf8'));
  }

  setupMiddleware() {
    this.app.use(express.json({
      limit: '10mb',
      verify: (req, res, buf) => {
        // Store raw body for webhook signature verification
        req.rawBody = buf;
      }
    }));

    // Rate limiting
    this.setupRateLimiting();

    // Request logging
    this.app.use((req, res, next) => {
      console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
      next();
    });
  }

  setupRateLimiting() {
    const rateLimit = this.config.webhooks.rateLimit;
    const requests = new Map();

    this.app.use((req, res, next) => {
      const clientId = req.ip;
      const now = Date.now();
      const windowStart = now - rateLimit.windowMs;

      if (!requests.has(clientId)) {
        requests.set(clientId, []);
      }

      const clientRequests = requests.get(clientId);
      // Remove old requests outside the window
      const recentRequests = clientRequests.filter(time => time > windowStart);

      if (recentRequests.length >= rateLimit.maxRequests) {
        return res.status(429).json({
          error: 'Too many requests',
          retryAfter: Math.ceil(rateLimit.windowMs / 1000)
        });
      }

      recentRequests.push(now);
      requests.set(clientId, recentRequests);

      next();
    });
  }

  setupRoutes() {
    // Health check
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        integrations: Object.keys(this.pmIntegration.integrations)
      });
    });

    // Jira webhooks
    if (this.config.integrations.jira.enabled) {
      this.app.post('/webhooks/jira', this.handleJiraWebhook.bind(this));
    }

    // Trello webhooks
    if (this.config.integrations.trello.enabled) {
      this.app.post('/webhooks/trello', this.handleTrelloWebhook.bind(this));
      this.app.head('/webhooks/trello', this.handleTrelloHead.bind(this));
    }

    // Asana webhooks
    if (this.config.integrations.asana.enabled) {
      this.app.post('/webhooks/asana', this.handleAsanaWebhook.bind(this));
    }

    // GitLab webhooks
    this.app.post('/webhooks/gitlab', this.handleGitlabWebhook.bind(this));

    // Generic webhook endpoint
    this.app.post('/webhooks/:tool', this.handleGenericWebhook.bind(this));

    // Status endpoint
    this.app.get('/status', async (req, res) => {
      try {
        const status = await this.pmIntegration.getProjectStatus();
        res.json({
          status: 'operational',
          timestamp: new Date().toISOString(),
          projectStatus: status
        });
      } catch (error) {
        res.status(500).json({
          status: 'error',
          error: error.message
        });
      }
    });

    // 404 handler
    this.app.use((req, res) => {
      res.status(404).json({
        error: 'Webhook endpoint not found',
        availableEndpoints: [
          '/webhooks/jira',
          '/webhooks/trello',
          '/webhooks/asana',
          '/webhooks/:tool'
        ]
      });
    });

    // Error handler
    this.app.use((error, req, res, next) => {
      console.error('Webhook server error:', error);
      res.status(500).json({
        error: 'Internal server error',
        timestamp: new Date().toISOString()
      });
    });
  }

  // Jira webhook handler
  async handleJiraWebhook(req, res) {
    try {
      // Verify Jira webhook signature
      if (!this.verifyJiraSignature(req)) {
        return res.status(401).json({ error: 'Invalid signature' });
      }

      const eventType = req.headers['x-jira-event'] || req.body.webhookEvent;
      const data = req.body;

      await this.pmIntegration.handleWebhook('jira', eventType, data);

      res.json({ status: 'processed' });
    } catch (error) {
      console.error('Jira webhook error:', error);
      res.status(500).json({ error: 'Processing failed' });
    }
  }

  // Trello webhook handler
  async handleTrelloWebhook(req, res) {
    try {
      const data = req.body;
      const eventType = this.mapTrelloEvent(data.action.type);

      await this.pmIntegration.handleWebhook('trello', eventType, data);

      res.json({ status: 'processed' });
    } catch (error) {
      console.error('Trello webhook error:', error);
      res.status(500).json({ error: 'Processing failed' });
    }
  }

  // Trello HEAD request for webhook verification
  handleTrelloHead(req, res) {
    res.status(200).end();
  }

  // Asana webhook handler
  async handleAsanaWebhook(req, res) {
    try {
      const data = req.body;
      const eventType = this.mapAsanaEvent(data.events[0]?.action || 'unknown');

      await this.pmIntegration.handleWebhook('asana', eventType, data);

      res.json({ status: 'processed' });
    } catch (error) {
      console.error('Asana webhook error:', error);
      res.status(500).json({ error: 'Processing failed' });
    }
  }

  // GitLab webhook handler
  async handleGitlabWebhook(req, res) {
    try {
      const eventType = req.headers['x-gitlab-event'];
      const data = req.body;

      // Verify GitLab webhook token if configured
      if (this.config.webhooks.gitlab?.webhookToken) {
        const token = req.headers['x-gitlab-token'];
        if (token !== this.config.webhooks.gitlab.webhookToken) {
          return res.status(401).json({ error: 'Invalid webhook token' });
        }
      }

      // Handle different GitLab events
      switch (eventType) {
        case 'Pipeline Hook':
          await this.handleGitlabPipelineEvent(data);
          break;
        case 'Job Hook':
          await this.handleGitlabJobEvent(data);
          break;
        case 'Merge Request Hook':
          await this.handleGitlabMergeRequestEvent(data);
          break;
        case 'Push Hook':
          await this.handleGitlabPushEvent(data);
          break;
        default:
          console.log(`ℹ️  Unhandled GitLab event: ${eventType}`);
      }

      res.json({ status: 'processed' });
    } catch (error) {
      console.error('GitLab webhook error:', error);
      res.status(500).json({ error: 'Processing failed' });
    }
  }

  // GitLab Pipeline event handler
  async handleGitlabPipelineEvent(data) {
    const pipeline = data.object_attributes;
    const project = data.project;

    console.log(`🔄 GitLab Pipeline: ${project.name} - ${pipeline.status}`);

    // Map GitLab pipeline status to our system events
    const eventType = `pipeline_${pipeline.status}`;

    await this.pmIntegration.handleWebhook('gitlab', eventType, {
      pipeline: {
        id: pipeline.id,
        status: pipeline.status,
        ref: pipeline.ref,
        sha: pipeline.sha,
        web_url: pipeline.web_url
      },
      project: {
        id: project.id,
        name: project.name,
        web_url: project.web_url
      },
      user: data.user,
      commit: data.commit
    });
  }

  // GitLab Job event handler
  async handleGitlabJobEvent(data) {
    const job = data.build;
    const project = data.project;

    console.log(`🔧 GitLab Job: ${project.name} - ${job.name} - ${job.status}`);

    const eventType = `job_${job.status}`;

    await this.pmIntegration.handleWebhook('gitlab', eventType, {
      job: {
        id: job.id,
        name: job.name,
        stage: job.stage,
        status: job.status,
        web_url: job.web_url,
        duration: job.duration
      },
      project: {
        id: project.id,
        name: project.name,
        web_url: project.web_url
      }
    });
  }

  // GitLab Merge Request event handler
  async handleGitlabMergeRequestEvent(data) {
    const mr = data.object_attributes;
    const project = data.project;

    console.log(`🔀 GitLab MR: ${project.name} - ${mr.title} - ${mr.state}`);

    const eventType = `merge_request_${mr.state}`;

    await this.pmIntegration.handleWebhook('gitlab', eventType, {
      merge_request: {
        id: mr.id,
        title: mr.title,
        description: mr.description,
        state: mr.state,
        web_url: mr.url,
        source_branch: mr.source_branch,
        target_branch: mr.target_branch
      },
      project: {
        id: project.id,
        name: project.name,
        web_url: project.web_url
      },
      user: data.user
    });
  }

  // GitLab Push event handler
  async handleGitlabPushEvent(data) {
    const project = data.project;
    const commits = data.commits || [];

    console.log(`📤 GitLab Push: ${project.name} - ${commits.length} commits`);

    await this.pmIntegration.handleWebhook('gitlab', 'push', {
      project: {
        id: project.id,
        name: project.name,
        web_url: project.web_url
      },
      ref: data.ref,
      checkout_sha: data.checkout_sha,
      commits: commits.map(commit => ({
        id: commit.id,
        message: commit.message,
        author: commit.author,
        url: commit.url
      })),
      user: data.user
    });
  }

  // Generic webhook handler for custom integrations
  async handleGenericWebhook(req, res) {
    try {
      const { tool } = req.params;
      const data = req.body;
      const eventType = req.headers['x-event-type'] || 'generic';

      await this.pmIntegration.handleWebhook(tool, eventType, data);

      res.json({ status: 'processed' });
    } catch (error) {
      console.error(`${req.params.tool} webhook error:`, error);
      res.status(500).json({ error: 'Processing failed' });
    }
  }

  // Signature verification methods
  verifyJiraSignature(req) {
    const signature = req.headers['x-hub-signature'];
    const secret = this.config.integrations.jira.webhookSecret;

    if (!signature || !secret) return true; // Skip verification if not configured

    const expectedSignature = crypto
      .createHmac('sha256', secret)
      .update(req.rawBody)
      .digest('hex');

    return crypto.timingSafeEqual(
      Buffer.from(signature.replace('sha256=', ''), 'hex'),
      Buffer.from(expectedSignature, 'hex')
    );
  }

  // Event mapping methods
  mapTrelloEvent(actionType) {
    const mapping = {
      'createCard': 'task_created',
      'updateCard': 'task_updated',
      'moveCardToBoard': 'task_created',
      'moveCardFromBoard': 'task_completed'
    };
    return mapping[actionType] || 'task_updated';
  }

  mapAsanaEvent(action) {
    const mapping = {
      'added': 'task_created',
      'changed': 'task_updated',
      'deleted': 'task_deleted',
      'undeleted': 'task_restored'
    };
    return mapping[action] || 'task_updated';
  }

  // Server management methods
  async start(port = this.config.webhooks.port) {
    return new Promise((resolve, reject) => {
      try {
        this.server = this.app.listen(port, () => {
          console.log(`🚀 Webhook server listening on port ${port}`);
          console.log(`📡 Webhook URL: ${this.config.webhooks.baseUrl}:${port}`);
          resolve(this.server);
        });
      } catch (error) {
        reject(error);
      }
    });
  }

  async stop() {
    if (this.server) {
      return new Promise((resolve) => {
        this.server.close(() => {
          console.log('🛑 Webhook server stopped');
          resolve();
        });
      });
    }
  }

  // Health monitoring
  getHealthStatus() {
    return {
      status: 'healthy',
      uptime: process.uptime(),
      integrations: Object.keys(this.pmIntegration.integrations),
      config: {
        port: this.config.webhooks.port,
        ssl: this.config.webhooks.ssl,
        rateLimit: this.config.webhooks.rateLimit
      }
    };
  }
}

module.exports = WebhookServer;
