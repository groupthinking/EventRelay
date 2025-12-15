/**
 * Performance Monitoring and Alerting System
 * Real-time performance tracking, alerting, and analytics
 */

const os = require('os');
const fs = require('fs');
const path = require('path');
const { EventEmitter } = require('events');

class PerformanceMonitor extends EventEmitter {
  constructor() {
    super();
    this.metrics = new Map();
    this.alerts = new Map();
    this.baselines = new Map();
    this.isMonitoring = false;
    this.monitoringInterval = null;

    this.config = this.loadConfig();
    this.thresholds = this.config.thresholds;

    // Initialize metrics collectors
    this.systemMetrics = {
      cpu: { usage: 0, history: [] },
      memory: { usage: 0, total: 0, free: 0, history: [] },
      disk: { usage: 0, total: 0, free: 0, history: [] },
      network: { rx: 0, tx: 0, history: [] }
    };

    this.appMetrics = {
      responseTime: { avg: 0, p95: 0, p99: 0, history: [] },
      throughput: { rps: 0, history: [] },
      errorRate: { percentage: 0, history: [] },
      activeConnections: { count: 0, history: [] },
      database: {
        connections: { active: 0, idle: 0, total: 0, history: [] },
        queryTime: { avg: 0, slow: 0, history: [] },
        connectionPool: { used: 0, available: 0, pending: 0, history: [] }
      },
      cache: {
        hitRate: { percentage: 0, history: [] },
        size: { used: 0, total: 0, history: [] },
        evictions: { count: 0, history: [] }
      }
    };
  }

  loadConfig() {
    const configPath = path.join(__dirname, '..', 'config', 'monitoring-config.json');

    if (fs.existsSync(configPath)) {
      return JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }

    // Default configuration
    return {
      enabled: true,
      interval: 30000, // 30 seconds
      retentionPeriod: 86400000, // 24 hours
      thresholds: {
        cpu: { warning: 70, critical: 90 },
        memory: { warning: 80, critical: 95 },
        disk: { warning: 85, critical: 95 },
        responseTime: { warning: 500, critical: 2000 }, // ms
        errorRate: { warning: 1, critical: 5 }, // percentage
        throughput: { min: 10, max: 1000 } // requests per second
      },
      alerts: {
        enabled: true,
        cooldown: 300000, // 5 minutes
        channels: {
          console: true,
          file: true,
          webhook: false,
          slack: false,
          email: false
        }
      },
      storage: {
        metrics: './monitoring/metrics/',
        alerts: './monitoring/alerts/',
        reports: './monitoring/reports/'
      }
    };
  }

  /**
   * Start performance monitoring
   */
  async start() {
    if (this.isMonitoring) {
      console.log('📊 Performance monitoring is already running');
      return;
    }

    console.log('🚀 Starting performance monitoring...');

    // Ensure storage directories exist
    this.ensureDirectories();

    // Load existing baselines
    await this.loadBaselines();

    // Start monitoring loop
    this.monitoringInterval = setInterval(() => {
      this.collectMetrics();
      this.checkThresholds();
      this.cleanupOldData();
    }, this.config.interval);

    this.isMonitoring = true;
    console.log('✅ Performance monitoring started');

    this.emit('started');
  }

  /**
   * Stop performance monitoring
   */
  async stop() {
    if (!this.isMonitoring) {
      console.log('📊 Performance monitoring is not running');
      return;
    }

    console.log('🛑 Stopping performance monitoring...');

    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }

    // Save final metrics
    await this.saveMetrics();

    this.isMonitoring = false;
    console.log('✅ Performance monitoring stopped');

    this.emit('stopped');
  }

  /**
   * Collect system and application metrics
   */
  collectMetrics() {
    const timestamp = Date.now();

    // System metrics
    this.collectSystemMetrics(timestamp);

    // Application metrics (would be populated from your app)
    this.collectAppMetrics(timestamp);

    // Emit metrics collected event
    this.emit('metricsCollected', {
      timestamp,
      system: this.systemMetrics,
      app: this.appMetrics
    });
  }

  /**
   * Collect system-level metrics
   */
  collectSystemMetrics(timestamp) {
    // CPU usage
    const cpuUsage = os.loadavg()[0] * 100 / os.cpus().length;
    this.systemMetrics.cpu.usage = cpuUsage;
    this.addToHistory(this.systemMetrics.cpu.history, { timestamp, value: cpuUsage });

    // Memory usage
    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    const usedMem = totalMem - freeMem;
    const memUsage = (usedMem / totalMem) * 100;

    this.systemMetrics.memory = {
      usage: memUsage,
      total: totalMem,
      free: freeMem,
      used: usedMem
    };
    this.addToHistory(this.systemMetrics.memory.history, { timestamp, value: memUsage });

    // Disk usage (simplified - would need more detailed implementation)
    const diskUsage = 45; // Placeholder - would calculate actual disk usage
    this.systemMetrics.disk.usage = diskUsage;
    this.addToHistory(this.systemMetrics.disk.history, { timestamp, value: diskUsage });
  }

  /**
   * Collect application-specific metrics
   */
  collectAppMetrics(timestamp) {
    // These would be populated by integrating with your application
    // For now, using placeholder values

    // Response time metrics
    const responseTime = Math.random() * 100 + 200; // 200-300ms range
    this.appMetrics.responseTime.avg = responseTime;
    this.addToHistory(this.appMetrics.responseTime.history, { timestamp, value: responseTime });

    // Throughput
    const throughput = Math.floor(Math.random() * 50) + 10; // 10-60 RPS
    this.appMetrics.throughput.rps = throughput;
    this.addToHistory(this.appMetrics.throughput.history, { timestamp, value: throughput });

    // Error rate
    const errorRate = Math.random() * 2; // 0-2%
    this.appMetrics.errorRate.percentage = errorRate;
    this.addToHistory(this.appMetrics.errorRate.history, { timestamp, value: errorRate });

    // Active connections
    const activeConnections = Math.floor(Math.random() * 100) + 50; // 50-150
    this.appMetrics.activeConnections.count = activeConnections;
    this.addToHistory(this.appMetrics.activeConnections.history, { timestamp, value: activeConnections });
  }

  /**
   * Check metrics against thresholds and trigger alerts
   */
  checkThresholds() {
    const alerts = [];

    // CPU alerts
    if (this.systemMetrics.cpu.usage > this.thresholds.cpu.critical) {
      alerts.push(this.createAlert('cpu', 'critical', this.systemMetrics.cpu.usage, this.thresholds.cpu.critical));
    } else if (this.systemMetrics.cpu.usage > this.thresholds.cpu.warning) {
      alerts.push(this.createAlert('cpu', 'warning', this.systemMetrics.cpu.usage, this.thresholds.cpu.warning));
    }

    // Memory alerts
    if (this.systemMetrics.memory.usage > this.thresholds.memory.critical) {
      alerts.push(this.createAlert('memory', 'critical', this.systemMetrics.memory.usage, this.thresholds.memory.critical));
    } else if (this.systemMetrics.memory.usage > this.thresholds.memory.warning) {
      alerts.push(this.createAlert('memory', 'warning', this.systemMetrics.memory.usage, this.thresholds.memory.warning));
    }

    // Response time alerts
    if (this.appMetrics.responseTime.avg > this.thresholds.responseTime.critical) {
      alerts.push(this.createAlert('responseTime', 'critical', this.appMetrics.responseTime.avg, this.thresholds.responseTime.critical));
    } else if (this.appMetrics.responseTime.avg > this.thresholds.responseTime.warning) {
      alerts.push(this.createAlert('responseTime', 'warning', this.appMetrics.responseTime.avg, this.thresholds.responseTime.warning));
    }

    // Error rate alerts
    if (this.appMetrics.errorRate.percentage > this.thresholds.errorRate.critical) {
      alerts.push(this.createAlert('errorRate', 'critical', this.appMetrics.errorRate.percentage, this.thresholds.errorRate.critical));
    } else if (this.appMetrics.errorRate.percentage > this.thresholds.errorRate.warning) {
      alerts.push(this.createAlert('errorRate', 'warning', this.appMetrics.errorRate.percentage, this.thresholds.errorRate.warning));
    }

    // Process alerts
    alerts.forEach(alert => this.processAlert(alert));
  }

  /**
   * Create alert object
   */
  createAlert(metric, severity, currentValue, threshold) {
    return {
      id: `${metric}_${severity}_${Date.now()}`,
      metric,
      severity,
      currentValue,
      threshold,
      timestamp: Date.now(),
      message: `${metric.toUpperCase()} ${severity}: ${currentValue.toFixed(2)} exceeds threshold ${threshold}`
    };
  }

  /**
   * Process alert (send notifications, log, etc.)
   */
  processAlert(alert) {
    // Check for alert cooldown
    const alertKey = `${alert.metric}_${alert.severity}`;
    const lastAlert = this.alerts.get(alertKey);

    if (lastAlert && (Date.now() - lastAlert.timestamp) < this.config.alerts.cooldown) {
      return; // Skip alert due to cooldown
    }

    // Store alert
    this.alerts.set(alertKey, alert);

    // Log alert
    console.log(`🚨 ALERT: ${alert.message}`);

    // Send notifications
    this.sendAlertNotifications(alert);

    // Emit alert event
    this.emit('alert', alert);

    // Save alert to file
    this.saveAlert(alert);
  }

  /**
   * Send alert notifications
   */
  sendAlertNotifications(alert) {
    if (!this.config.alerts.enabled) return;

    const channels = this.config.alerts.channels;

    if (channels.console) {
      console.log(`🚨 ${alert.severity.toUpperCase()}: ${alert.message}`);
    }

    if (channels.file) {
      this.saveAlertToFile(alert);
    }

    // Additional channels would be implemented here
    if (channels.webhook) {
      this.sendWebhookAlert(alert);
    }

    if (channels.slack) {
      this.sendSlackAlert(alert);
    }

    if (channels.email) {
      this.sendEmailAlert(alert);
    }
  }

  /**
   * Save alert to file
   */
  saveAlertToFile(alert) {
    const alertFile = path.join(this.config.storage.alerts, `alert_${alert.id}.json`);
    fs.writeFileSync(alertFile, JSON.stringify(alert, null, 2));
  }

  /**
   * Save metrics to file
   */
  async saveMetrics() {
    const metricsFile = path.join(this.config.storage.metrics, `metrics_${Date.now()}.json`);
    const metrics = {
      timestamp: Date.now(),
      system: this.systemMetrics,
      app: this.appMetrics
    };

    fs.writeFileSync(metricsFile, JSON.stringify(metrics, null, 2));
  }

  /**
   * Load performance baselines
   */
  async loadBaselines() {
    const baselineFile = path.join(__dirname, '..', 'config', 'performance-baselines.json');

    if (fs.existsSync(baselineFile)) {
      const baselines = JSON.parse(fs.readFileSync(baselineFile, 'utf8'));
      Object.assign(this.baselines, baselines);
    } else {
      // Create default baselines
      this.baselines = {
        cpu: { warning: 70, critical: 90 },
        memory: { warning: 80, critical: 95 },
        responseTime: { warning: 500, critical: 2000 },
        errorRate: { warning: 1, critical: 5 },
        throughput: { min: 10, max: 1000 }
      };
      this.saveBaselines();
    }
  }

  /**
   * Save performance baselines
   */
  saveBaselines() {
    const baselineFile = path.join(__dirname, '..', 'config', 'performance-baselines.json');
    fs.writeFileSync(baselineFile, JSON.stringify(this.baselines, null, 2));
  }

  /**
   * Ensure required directories exist
   */
  ensureDirectories() {
    const dirs = [
      this.config.storage.metrics,
      this.config.storage.alerts,
      this.config.storage.reports
    ];

    dirs.forEach(dir => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    });
  }

  /**
   * Add value to metric history
   */
  addToHistory(history, entry) {
    history.push(entry);

    // Keep only recent data (last 24 hours worth)
    const cutoff = Date.now() - this.config.retentionPeriod;
    const filtered = history.filter(item => item.timestamp > cutoff);

    // Replace array contents
    history.splice(0, history.length, ...filtered);
  }

  /**
   * Clean up old data
   */
  cleanupOldData() {
    const cutoff = Date.now() - this.config.retentionPeriod;

    // Clean up metric histories
    Object.values(this.systemMetrics).forEach(metric => {
      if (metric.history) {
        metric.history = metric.history.filter(item => item.timestamp > cutoff);
      }
    });

    Object.values(this.appMetrics).forEach(metric => {
      if (metric.history) {
        metric.history = metric.history.filter(item => item.timestamp > cutoff);
      }
    });
  }

  /**
   * Generate performance report
   */
  generateReport() {
    const report = {
      timestamp: new Date().toISOString(),
      period: 'last_24_hours',
      summary: {
        averageCpu: this.calculateAverage(this.systemMetrics.cpu.history),
        averageMemory: this.calculateAverage(this.systemMetrics.memory.history),
        averageResponseTime: this.calculateAverage(this.appMetrics.responseTime.history),
        averageThroughput: this.calculateAverage(this.appMetrics.throughput.history),
        averageErrorRate: this.calculateAverage(this.appMetrics.errorRate.history),
        totalAlerts: this.alerts.size
      },
      trends: this.calculateTrends(),
      recommendations: this.generateRecommendations()
    };

    return report;
  }

  /**
   * Calculate average from history
   */
  calculateAverage(history) {
    if (history.length === 0) return 0;
    const sum = history.reduce((acc, item) => acc + item.value, 0);
    return sum / history.length;
  }

  /**
   * Calculate performance trends
   */
  calculateTrends() {
    const trends = {};

    // CPU trend
    const cpuHistory = this.systemMetrics.cpu.history;
    if (cpuHistory.length >= 2) {
      const recent = cpuHistory.slice(-10); // Last 10 readings
      const older = cpuHistory.slice(-20, -10); // Previous 10 readings

      const recentAvg = this.calculateAverage(recent);
      const olderAvg = this.calculateAverage(older);

      trends.cpu = {
        direction: recentAvg > olderAvg ? 'increasing' : 'decreasing',
        change: ((recentAvg - olderAvg) / olderAvg) * 100
      };
    }

    // Similar calculations for other metrics...

    return trends;
  }

  /**
   * Generate performance recommendations
   */
  generateRecommendations() {
    const recommendations = [];

    // CPU recommendations
    if (this.systemMetrics.cpu.usage > this.thresholds.cpu.warning) {
      recommendations.push('Consider optimizing CPU-intensive operations or scaling compute resources');
    }

    // Memory recommendations
    if (this.systemMetrics.memory.usage > this.thresholds.memory.warning) {
      recommendations.push('Monitor memory usage patterns and consider memory optimization techniques');
    }

    // Response time recommendations
    if (this.appMetrics.responseTime.avg > this.thresholds.responseTime.warning) {
      recommendations.push('Optimize database queries, implement caching, or scale application servers');
    }

    // Error rate recommendations
    if (this.appMetrics.errorRate.percentage > this.thresholds.errorRate.warning) {
      recommendations.push('Investigate error patterns and improve error handling and logging');
    }

    return recommendations;
  }

  /**
   * Get current status
   */
  getStatus() {
    return {
      isMonitoring: this.isMonitoring,
      uptime: this.isMonitoring ? Date.now() - (this.startTime || Date.now()) : 0,
      metrics: {
        system: this.systemMetrics,
        app: this.appMetrics
      },
      alerts: Array.from(this.alerts.values()),
      config: this.config
    };
  }

  // Placeholder methods for external integrations
  sendWebhookAlert(alert) { console.log('Webhook alert would be sent:', alert.message); }
  sendSlackAlert(alert) { console.log('Slack alert would be sent:', alert.message); }
  sendEmailAlert(alert) { console.log('Email alert would be sent:', alert.message); }
  saveAlert(alert) { /* Implementation would save to persistent storage */ }
}

module.exports = PerformanceMonitor;
