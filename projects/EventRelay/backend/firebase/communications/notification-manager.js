/**
 * Communication Integration Manager
 * Multi-platform notification system for alerts, reports, and updates
 */

const axios = require('axios');
const nodemailer = require('nodemailer');
const { WebClient } = require('@slack/web-api');
const { Client } = require('@microsoft/microsoft-graph-client');
const fs = require('fs');
const path = require('path');
const { EventEmitter } = require('events');

class NotificationManager extends EventEmitter {
  constructor() {
    super();
    this.transporters = new Map();
    this.templates = new Map();
    this.webhooks = new Map();

    this.config = this.loadConfig();
    this.initializeTransporters();
    this.loadTemplates();
  }

  loadConfig() {
    const configPath = path.join(__dirname, '..', 'config', 'communication-config.json');

    if (fs.existsSync(configPath)) {
      return JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }

    return {
      enabled: true,
      rateLimiting: {
        maxRequests: 100,
        windowMs: 60000, // 1 minute
        retryDelay: 5000
      },
      channels: {
        slack: {
          enabled: false,
          token: process.env.SLACK_BOT_TOKEN,
          defaultChannel: '#alerts',
          webhooks: {
            alerts: process.env.SLACK_ALERTS_WEBHOOK,
            reports: process.env.SLACK_REPORTS_WEBHOOK,
            notifications: process.env.SLACK_NOTIFICATIONS_WEBHOOK
          }
        },
        teams: {
          enabled: false,
          clientId: process.env.TEAMS_CLIENT_ID,
          clientSecret: process.env.TEAMS_CLIENT_SECRET,
          tenantId: process.env.TEAMS_TENANT_ID,
          webhooks: {
            alerts: process.env.TEAMS_ALERTS_WEBHOOK,
            reports: process.env.TEAMS_REPORTS_WEBHOOK
          }
        },
        discord: {
          enabled: false,
          token: process.env.DISCORD_BOT_TOKEN,
          defaultChannel: process.env.DISCORD_CHANNEL_ID,
          webhooks: {
            alerts: process.env.DISCORD_ALERTS_WEBHOOK,
            reports: process.env.DISCORD_REPORTS_WEBHOOK
          }
        },
        email: {
          enabled: false,
          smtp: {
            host: 'smtp.gmail.com',
            port: 587,
            secure: false,
            auth: {
              user: process.env.EMAIL_USER,
              pass: process.env.EMAIL_PASS
            }
          },
          from: 'Firebase System <noreply@firebase.com>',
          templates: {
            alerts: './communications/templates/alert-email.html',
            reports: './communications/templates/report-email.html',
            notifications: './communications/templates/notification-email.html'
          }
        },
        webhook: {
          enabled: false,
          endpoints: {
            alerts: process.env.GENERIC_ALERTS_WEBHOOK,
            reports: process.env.GENERIC_REPORTS_WEBHOOK
          },
          headers: {
            'Authorization': `Bearer ${process.env.WEBHOOK_TOKEN}`,
            'Content-Type': 'application/json'
          }
        }
      },
      templates: {
        alert: {
          slack: ':warning: *{title}*\n{description}\n*Severity:* {severity}\n*Time:* {timestamp}',
          teams: {
            '@type': 'MessageCard',
            '@context': 'http://schema.org/extensions',
            'themeColor': 'FF0000',
            'title': '{title}',
            'text': '{description}',
            'sections': [{
              'facts': [
                { 'name': 'Severity:', 'value': '{severity}' },
                { 'name': 'Time:', 'value': '{timestamp}' }
              ]
            }]
          }
        },
        report: {
          slack: ':chart_with_upwards_trend: *{title}*\n{summary}\n[View Full Report]({link})',
          email: {
            subject: '📊 {title} - {date}',
            html: '<h1>{title}</h1><p>{summary}</p><a href="{link}">View Full Report</a>'
          }
        }
      }
    };
  }

  /**
   * Initialize communication transporters
   */
  initializeTransporters() {
    const channels = this.config.channels;

    // Slack
    if (channels.slack.enabled && channels.slack.token) {
      this.transporters.set('slack', new WebClient(channels.slack.token));
    }

    // Email
    if (channels.email.enabled && channels.email.smtp) {
      this.transporters.set('email', nodemailer.createTransporter(channels.email.smtp));
    }

    // Microsoft Teams
    if (channels.teams.enabled) {
      this.initializeTeamsClient();
    }

    console.log(`✅ Initialized ${this.transporters.size} communication transporters`);
  }

  /**
   * Initialize Microsoft Teams client
   */
  initializeTeamsClient() {
    const teams = this.config.channels.teams;

    if (teams.clientId && teams.clientSecret && teams.tenantId) {
      // Teams client initialization would go here
      // This requires Microsoft Graph SDK setup
      console.log('ℹ️ Teams client initialization would be implemented here');
    }
  }

  /**
   * Load notification templates
   */
  loadTemplates() {
    const templatesDir = path.join(__dirname, 'templates');

    if (!fs.existsSync(templatesDir)) {
      fs.mkdirSync(templatesDir, { recursive: true });
    }

    // Load email templates
    const emailTemplates = [
      'alert-email.html',
      'alert-email.txt',
      'report-email.html',
      'report-email.txt',
      'notification-email.html',
      'notification-email.txt'
    ];

    for (const template of emailTemplates) {
      const templatePath = path.join(templatesDir, template);
      if (fs.existsSync(templatePath)) {
        this.templates.set(template, fs.readFileSync(templatePath, 'utf8'));
      }
    }

    console.log(`✅ Loaded ${this.templates.size} notification templates`);
  }

  /**
   * Send alert notification
   */
  async sendAlert(alert) {
    const message = {
      title: alert.title || 'System Alert',
      description: alert.message || alert.description,
      severity: alert.severity || 'medium',
      timestamp: new Date().toLocaleString(),
      type: 'alert',
      data: alert
    };

    await this.sendToChannels(message);
    this.emit('alertSent', alert);
  }

  /**
   * Send report notification
   */
  async sendReport(report) {
    const message = {
      title: report.title || 'System Report',
      summary: report.summary || 'Report generated',
      date: new Date().toISOString().split('T')[0],
      link: report.link || '#',
      type: 'report',
      data: report
    };

    await this.sendToChannels(message);
    this.emit('reportSent', report);
  }

  /**
   * Send general notification
   */
  async sendNotification(notification) {
    const message = {
      title: notification.title || 'System Notification',
      description: notification.message || notification.description,
      type: 'notification',
      timestamp: new Date().toLocaleString(),
      data: notification
    };

    await this.sendToChannels(message);
    this.emit('notificationSent', notification);
  }

  /**
   * Send message to all configured channels
   */
  async sendToChannels(message) {
    const channels = this.config.channels;
    const promises = [];

    // Slack
    if (channels.slack.enabled) {
      promises.push(this.sendToSlack(message));
    }

    // Microsoft Teams
    if (channels.teams.enabled) {
      promises.push(this.sendToTeams(message));
    }

    // Discord
    if (channels.discord.enabled) {
      promises.push(this.sendToDiscord(message));
    }

    // Email
    if (channels.email.enabled) {
      promises.push(this.sendToEmail(message));
    }

    // Generic webhook
    if (channels.webhook.enabled) {
      promises.push(this.sendToWebhook(message));
    }

    try {
      await Promise.allSettled(promises);
    } catch (error) {
      console.error('❌ Error sending notifications:', error.message);
    }
  }

  /**
   * Send message to Slack
   */
  async sendToSlack(message) {
    try {
      const slack = this.transporters.get('slack');
      if (!slack) return;

      const channels = this.config.channels.slack;
      const channel = this.getChannelForMessage(message, channels.webhooks);

      const formattedMessage = this.formatSlackMessage(message);

      if (channel && channels.webhooks[channel]) {
        // Send to webhook
        await axios.post(channels.webhooks[channel], {
          text: formattedMessage,
          username: 'Firebase System',
          icon_emoji: ':robot_face:'
        });
      } else {
        // Send via API
        await slack.chat.postMessage({
          channel: channels.defaultChannel,
          text: formattedMessage,
          username: 'Firebase System'
        });
      }

      console.log('✅ Slack notification sent');
    } catch (error) {
      console.error('❌ Slack notification failed:', error.message);
    }
  }

  /**
   * Send message to Microsoft Teams
   */
  async sendToTeams(message) {
    try {
      const teams = this.config.channels.teams;
      const webhook = this.getChannelForMessage(message, teams.webhooks);

      if (webhook && teams.webhooks[webhook]) {
        const formattedMessage = this.formatTeamsMessage(message);

        await axios.post(teams.webhooks[webhook], formattedMessage, {
          headers: { 'Content-Type': 'application/json' }
        });

        console.log('✅ Teams notification sent');
      }
    } catch (error) {
      console.error('❌ Teams notification failed:', error.message);
    }
  }

  /**
   * Send message to Discord
   */
  async sendToDiscord(message) {
    try {
      const discord = this.config.channels.discord;
      const webhook = this.getChannelForMessage(message, discord.webhooks);

      if (webhook && discord.webhooks[webhook]) {
        const formattedMessage = {
          content: this.formatDiscordMessage(message),
          username: 'Firebase System',
          avatar_url: 'https://example.com/avatar.png'
        };

        await axios.post(discord.webhooks[webhook], formattedMessage);

        console.log('✅ Discord notification sent');
      }
    } catch (error) {
      console.error('❌ Discord notification failed:', error.message);
    }
  }

  /**
   * Send message via email
   */
  async sendToEmail(message) {
    try {
      const email = this.transporters.get('email');
      if (!email) return;

      const config = this.config.channels.email;
      const template = this.getEmailTemplate(message);

      const mailOptions = {
        from: config.from,
        to: message.recipients || config.defaultRecipients,
        subject: this.formatEmailSubject(message, template),
        html: this.formatEmailBody(message, template)
      };

      await email.sendMail(mailOptions);
      console.log('✅ Email notification sent');
    } catch (error) {
      console.error('❌ Email notification failed:', error.message);
    }
  }

  /**
   * Send message to generic webhook
   */
  async sendToWebhook(message) {
    try {
      const webhook = this.config.channels.webhook;
      const endpoint = this.getChannelForMessage(message, webhook.endpoints);

      if (endpoint && webhook.endpoints[endpoint]) {
        await axios.post(webhook.endpoints[endpoint], {
          ...message,
          timestamp: new Date().toISOString()
        }, {
          headers: webhook.headers
        });

        console.log('✅ Webhook notification sent');
      }
    } catch (error) {
      console.error('❌ Webhook notification failed:', error.message);
    }
  }

  /**
   * Get appropriate channel for message type
   */
  getChannelForMessage(message, webhooks) {
    switch (message.type) {
      case 'alert':
        return 'alerts';
      case 'report':
        return 'reports';
      case 'notification':
        return 'notifications';
      default:
        return 'alerts';
    }
  }

  /**
   * Format message for Slack
   */
  formatSlackMessage(message) {
    const template = this.config.templates.alert.slack;
    return template
      .replace('{title}', message.title)
      .replace('{description}', message.description)
      .replace('{severity}', message.severity || 'medium')
      .replace('{timestamp}', message.timestamp);
  }

  /**
   * Format message for Microsoft Teams
   */
  formatTeamsMessage(message) {
    const template = this.config.templates.alert.teams;
    return {
      ...template,
      title: template.title.replace('{title}', message.title),
      text: template.text.replace('{description}', message.description),
      sections: [{
        facts: [
          { name: 'Severity:', value: message.severity || 'medium' },
          { name: 'Time:', value: message.timestamp }
        ]
      }]
    };
  }

  /**
   * Format message for Discord
   */
  formatDiscordMessage(message) {
    let emoji = '📢';
    if (message.type === 'alert') {
      emoji = message.severity === 'critical' ? '🚨' : '⚠️';
    } else if (message.type === 'report') {
      emoji = '📊';
    }

    return `${emoji} **${message.title}**\n${message.description}\n*Severity: ${message.severity || 'medium'}*\n*Time: ${message.timestamp}*`;
  }

  /**
   * Get email template for message type
   */
  getEmailTemplate(message) {
    const config = this.config.channels.email;
    const templates = config.templates;

    switch (message.type) {
      case 'alert':
        return templates.alerts;
      case 'report':
        return templates.reports;
      case 'notification':
        return templates.notifications;
      default:
        return templates.notifications;
    }
  }

  /**
   * Format email subject
   */
  formatEmailSubject(message, template) {
    if (template && template.subject) {
      return template.subject
        .replace('{title}', message.title)
        .replace('{date}', new Date().toISOString().split('T')[0]);
    }

    return `${message.title} - ${new Date().toISOString().split('T')[0]}`;
  }

  /**
   * Format email body
   */
  formatEmailBody(message, template) {
    if (template && template.html) {
      return template.html
        .replace('{title}', message.title)
        .replace('{summary}', message.description || message.summary || '')
        .replace('{link}', message.link || '#');
    }

    return `
      <h1>${message.title}</h1>
      <p>${message.description || message.summary || ''}</p>
      <p><strong>Type:</strong> ${message.type}</p>
      <p><strong>Severity:</strong> ${message.severity || 'medium'}</p>
      <p><strong>Time:</strong> ${message.timestamp}</p>
    `;
  }

  /**
   * Send bulk notifications
   */
  async sendBulkNotifications(notifications) {
    console.log(`📤 Sending ${notifications.length} bulk notifications...`);

    const promises = notifications.map(notification => {
      switch (notification.type) {
        case 'alert':
          return this.sendAlert(notification);
        case 'report':
          return this.sendReport(notification);
        default:
          return this.sendNotification(notification);
      }
    });

    const results = await Promise.allSettled(promises);
    const successful = results.filter(result => result.status === 'fulfilled').length;
    const failed = results.filter(result => result.status === 'rejected').length;

    console.log(`✅ Bulk notifications: ${successful} sent, ${failed} failed`);
    this.emit('bulkNotificationsSent', { successful, failed, total: notifications.length });
  }

  /**
   * Test all communication channels
   */
  async testCommunications() {
    console.log('🧪 Testing communication channels...');

    const testMessage = {
      title: 'Communication Test',
      description: 'This is a test message from Firebase System',
      type: 'notification',
      severity: 'low'
    };

    await this.sendToChannels(testMessage);
    console.log('✅ Communication test completed');
  }

  /**
   * Get communication status
   */
  getStatus() {
    const channels = this.config.channels;
    const status = {
      enabled: this.config.enabled,
      channels: {},
      transporters: Array.from(this.transporters.keys()),
      templates: this.templates.size
    };

    for (const [channelName, channelConfig] of Object.entries(channels)) {
      status.channels[channelName] = {
        enabled: channelConfig.enabled,
        configured: this.isChannelConfigured(channelConfig)
      };
    }

    return status;
  }

  /**
   * Check if channel is properly configured
   */
  isChannelConfigured(channelConfig) {
    if (!channelConfig.enabled) return false;

    // Check for required configuration based on channel type
    switch (channelConfig.type || 'generic') {
      case 'slack':
        return !!(channelConfig.token || channelConfig.webhooks);
      case 'email':
        return !!(channelConfig.smtp && channelConfig.smtp.auth);
      case 'webhook':
        return !!(channelConfig.endpoints);
      default:
        return true;
    }
  }

  /**
   * Get communication statistics
   */
  getStatistics() {
    // This would track sent messages, failures, etc.
    // For now, return basic info
    return {
      channels: Object.keys(this.config.channels),
      templates: this.templates.size,
      transporters: this.transporters.size,
      lastActivity: new Date().toISOString()
    };
  }
}

module.exports = NotificationManager;
