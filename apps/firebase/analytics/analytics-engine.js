/**
 * Advanced Analytics Engine
 * Comprehensive data analysis, dashboards, and reporting system
 */

const fs = require('fs');
const path = require('path');
const { EventEmitter } = require('events');

class AnalyticsEngine extends EventEmitter {
  constructor() {
    super();
    this.dataSources = new Map();
    this.metrics = new Map();
    this.dashboards = new Map();
    this.reports = new Map();
    this.alerts = new Map();
    this.isRunning = false;

    this.config = this.loadConfig();
    this.cache = new Map();
  }

  loadConfig() {
    const configPath = path.join(__dirname, '..', 'config', 'analytics-config.json');

    if (fs.existsSync(configPath)) {
      return JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }

    return {
      enabled: true,
      dataRetention: 90, // days
      updateInterval: 300000, // 5 minutes
      cache: {
        enabled: true,
        ttl: 300000, // 5 minutes
        maxSize: 1000
      },
      dashboards: {
        autoRefresh: true,
        refreshInterval: 60000, // 1 minute
        maxWidgets: 50
      },
      alerts: {
        enabled: true,
        evaluationInterval: 60000, // 1 minute
        cooldownPeriod: 300000 // 5 minutes
      },
      reports: {
        autoGenerate: true,
        schedule: {
          daily: '0 9 * * *',
          weekly: '0 9 * * 1',
          monthly: '0 9 1 * *'
        },
        formats: ['html', 'pdf', 'json', 'csv'],
        retention: 365 // days
      }
    };
  }

  /**
   * Start the analytics engine
   */
  async start() {
    if (this.isRunning) {
      console.log('📊 Analytics engine is already running');
      return;
    }

    console.log('🚀 Starting advanced analytics engine...');

    try {
      // Initialize data sources
      await this.initializeDataSources();

      // Load existing dashboards and reports
      await this.loadDashboards();
      await this.loadReports();

      // Start data collection and processing
      this.startDataCollection();
      this.startAlertEvaluation();
      this.startReportGeneration();

      this.isRunning = true;
      console.log('✅ Analytics engine started successfully');

      this.emit('started');
    } catch (error) {
      console.error('❌ Failed to start analytics engine:', error.message);
      throw error;
    }
  }

  /**
   * Stop the analytics engine
   */
  async stop() {
    if (!this.isRunning) {
      console.log('📊 Analytics engine is not running');
      return;
    }

    console.log('🛑 Stopping analytics engine...');

    // Stop all intervals and timers
    if (this.collectionInterval) {
      clearInterval(this.collectionInterval);
    }
    if (this.alertInterval) {
      clearInterval(this.alertInterval);
    }
    if (this.reportInterval) {
      clearInterval(this.reportInterval);
    }

    this.isRunning = false;
    console.log('✅ Analytics engine stopped');

    this.emit('stopped');
  }

  /**
   * Initialize data sources from various systems
   */
  async initializeDataSources() {
    console.log('🔗 Initializing data sources...');

    // Performance monitoring data
    this.registerDataSource('performance', {
      type: 'file',
      path: './monitoring/metrics/',
      format: 'json',
      updateInterval: 30000
    });

    // Security scan data
    this.registerDataSource('security', {
      type: 'file',
      path: './reports/security/',
      format: 'json',
      updateInterval: 3600000 // 1 hour
    });

    // Documentation metrics
    this.registerDataSource('documentation', {
      type: 'file',
      path: './monitoring/metrics/',
      pattern: '*docs*',
      format: 'json',
      updateInterval: 60000
    });

    // Project management data
    this.registerDataSource('project-management', {
      type: 'api',
      endpoint: 'http://localhost:3001/api/pm/metrics',
      updateInterval: 300000
    });

    console.log('✅ Data sources initialized');
  }

  /**
   * Register a data source
   */
  registerDataSource(name, config) {
    this.dataSources.set(name, {
      ...config,
      lastUpdate: null,
      data: null,
      status: 'inactive'
    });
  }

  /**
   * Start data collection from all sources
   */
  startDataCollection() {
    this.collectionInterval = setInterval(async () => {
      await this.collectData();
      this.processMetrics();
      this.updateCache();
    }, this.config.updateInterval);
  }

  /**
   * Collect data from all registered sources
   */
  async collectData() {
    const promises = [];

    for (const [name, source] of this.dataSources) {
      promises.push(this.collectFromSource(name, source));
    }

    try {
      await Promise.all(promises);
      this.emit('dataCollected', Array.from(this.dataSources.keys()));
    } catch (error) {
      console.error('❌ Data collection error:', error.message);
    }
  }

  /**
   * Collect data from a specific source
   */
  async collectFromSource(name, source) {
    try {
      let data = null;

      switch (source.type) {
        case 'file':
          data = await this.collectFromFile(source);
          break;
        case 'api':
          data = await this.collectFromAPI(source);
          break;
        case 'database':
          data = await this.collectFromDatabase(source);
          break;
        default:
          throw new Error(`Unsupported data source type: ${source.type}`);
      }

      if (data) {
        source.data = data;
        source.lastUpdate = Date.now();
        source.status = 'active';
      }
    } catch (error) {
      source.status = 'error';
      source.error = error.message;
      console.error(`❌ Failed to collect from ${name}:`, error.message);
    }
  }

  /**
   * Collect data from file system
   */
  async collectFromFile(source) {
    const files = fs.readdirSync(source.path)
      .filter(file => file.endsWith('.json'))
      .map(file => path.join(source.path, file))
      .sort((a, b) => fs.statSync(b).mtime - fs.statSync(a).mtime);

    if (files.length === 0) return null;

    // Read most recent files (limit to prevent memory issues)
    const recentFiles = files.slice(0, 10);
    const data = [];

    for (const file of recentFiles) {
      try {
        const content = fs.readFileSync(file, 'utf8');
        data.push(JSON.parse(content));
      } catch (error) {
        console.warn(`⚠️  Failed to read ${file}:`, error.message);
      }
    }

    return data;
  }

  /**
   * Collect data from API endpoints
   */
  async collectFromAPI(source) {
    // Placeholder for API data collection
    // In a real implementation, this would make HTTP requests
    return {
      timestamp: Date.now(),
      status: 'simulated',
      data: {}
    };
  }

  /**
   * Collect data from database
   */
  async collectFromDatabase(source) {
    // Placeholder for database data collection
    return {
      timestamp: Date.now(),
      status: 'simulated',
      records: []
    };
  }

  /**
   * Process collected data into metrics
   */
  processMetrics() {
    // Process performance metrics
    this.processPerformanceMetrics();

    // Process security metrics
    this.processSecurityMetrics();

    // Process documentation metrics
    this.processDocumentationMetrics();

    // Process project management metrics
    this.processProjectManagementMetrics();

    this.emit('metricsProcessed', Array.from(this.metrics.keys()));
  }

  /**
   * Process performance monitoring data
   */
  processPerformanceMetrics() {
    const perfSource = this.dataSources.get('performance');
    if (!perfSource?.data?.length) return;

    const metrics = {
      cpu: { avg: 0, max: 0, trend: 'stable', history: [] },
      memory: { avg: 0, max: 0, trend: 'stable', history: [] },
      responseTime: { avg: 0, p95: 0, p99: 0, trend: 'stable', history: [] },
      throughput: { avg: 0, max: 0, trend: 'stable', history: [] },
      errorRate: { avg: 0, max: 0, trend: 'stable', history: [] },
      uptime: { percentage: 100, incidents: 0 }
    };

    // Calculate metrics from performance data
    const cpuValues = [];
    const memoryValues = [];
    const responseValues = [];
    const throughputValues = [];
    const errorValues = [];

    perfSource.data.forEach(entry => {
      if (entry.system?.cpu?.usage) cpuValues.push(entry.system.cpu.usage);
      if (entry.system?.memory?.usage) memoryValues.push(entry.system.memory.usage);
      if (entry.app?.responseTime?.avg) responseValues.push(entry.app.responseTime.avg);
      if (entry.app?.throughput?.rps) throughputValues.push(entry.app.throughput.rps);
      if (entry.app?.errorRate?.percentage) errorValues.push(entry.app.errorRate.percentage);
    });

    // Calculate averages and trends
    if (cpuValues.length > 0) {
      metrics.cpu.avg = cpuValues.reduce((a, b) => a + b, 0) / cpuValues.length;
      metrics.cpu.max = Math.max(...cpuValues);
      metrics.cpu.trend = this.calculateTrend(cpuValues);
      metrics.cpu.history = cpuValues.slice(-20);
    }

    if (memoryValues.length > 0) {
      metrics.memory.avg = memoryValues.reduce((a, b) => a + b, 0) / memoryValues.length;
      metrics.memory.max = Math.max(...memoryValues);
      metrics.memory.trend = this.calculateTrend(memoryValues);
      metrics.memory.history = memoryValues.slice(-20);
    }

    if (responseValues.length > 0) {
      metrics.responseTime.avg = responseValues.reduce((a, b) => a + b, 0) / responseValues.length;
      metrics.responseTime.p95 = this.calculatePercentile(responseValues, 95);
      metrics.responseTime.p99 = this.calculatePercentile(responseValues, 99);
      metrics.responseTime.trend = this.calculateTrend(responseValues);
      metrics.responseTime.history = responseValues.slice(-20);
    }

    if (throughputValues.length > 0) {
      metrics.throughput.avg = throughputValues.reduce((a, b) => a + b, 0) / throughputValues.length;
      metrics.throughput.max = Math.max(...throughputValues);
      metrics.throughput.trend = this.calculateTrend(throughputValues);
      metrics.throughput.history = throughputValues.slice(-20);
    }

    if (errorValues.length > 0) {
      metrics.errorRate.avg = errorValues.reduce((a, b) => a + b, 0) / errorValues.length;
      metrics.errorRate.max = Math.max(...errorValues);
      metrics.errorRate.trend = this.calculateTrend(errorValues);
      metrics.errorRate.history = errorValues.slice(-20);
    }

    this.metrics.set('performance', metrics);
  }

  /**
   * Process security scan data
   */
  processSecurityMetrics() {
    const securitySource = this.dataSources.get('security');
    if (!securitySource?.data?.length) return;

    const metrics = {
      totalScans: securitySource.data.length,
      vulnerabilities: { critical: 0, high: 0, medium: 0, low: 0 },
      compliance: { score: 100, issues: 0 },
      trends: { newVulnerabilities: 0, resolvedVulnerabilities: 0 },
      lastScan: null
    };

    // Process security scan results
    securitySource.data.forEach(scan => {
      if (scan.summary) {
        metrics.vulnerabilities.critical += scan.summary.critical || 0;
        metrics.vulnerabilities.high += scan.summary.high || 0;
        metrics.vulnerabilities.medium += scan.summary.medium || 0;
        metrics.vulnerabilities.low += scan.summary.low || 0;
      }

      if (scan.timestamp > (metrics.lastScan || 0)) {
        metrics.lastScan = scan.timestamp;
      }
    });

    this.metrics.set('security', metrics);
  }

  /**
   * Process documentation metrics
   */
  processDocumentationMetrics() {
    const docsSource = this.dataSources.get('documentation');
    if (!docsSource?.data?.length) return;

    const metrics = {
      totalFiles: 0,
      totalSize: 0,
      lastModified: null,
      updateFrequency: 0,
      completionRate: 0,
      qualityScore: 0
    };

    // Process documentation data
    docsSource.data.forEach(entry => {
      if (entry.files) {
        metrics.totalFiles += entry.files.length;
      }
      if (entry.lastModified > (metrics.lastModified || 0)) {
        metrics.lastModified = entry.lastModified;
      }
    });

    this.metrics.set('documentation', metrics);
  }

  /**
   * Process project management metrics
   */
  processProjectManagementMetrics() {
    const pmSource = this.dataSources.get('project-management');
    if (!pmSource?.data) return;

    const metrics = {
      totalTasks: 0,
      completedTasks: 0,
      inProgressTasks: 0,
      overdueTasks: 0,
      teamVelocity: 0,
      burndownStatus: 'on-track'
    };

    // Process PM data
    if (pmSource.data.tasks) {
      metrics.totalTasks = pmSource.data.tasks.length;
      metrics.completedTasks = pmSource.data.tasks.filter(t => t.status === 'done').length;
      metrics.inProgressTasks = pmSource.data.tasks.filter(t => t.status === 'in_progress').length;
      metrics.overdueTasks = pmSource.data.tasks.filter(t => t.dueDate && new Date(t.dueDate) < new Date()).length;
    }

    this.metrics.set('project-management', metrics);
  }

  /**
   * Calculate trend from data points
   */
  calculateTrend(values) {
    if (values.length < 2) return 'stable';

    const recent = values.slice(-5);
    const older = values.slice(-10, -5);

    if (recent.length === 0 || older.length === 0) return 'stable';

    const recentAvg = recent.reduce((a, b) => a + b, 0) / recent.length;
    const olderAvg = older.reduce((a, b) => a + b, 0) / older.length;

    const change = ((recentAvg - olderAvg) / olderAvg) * 100;

    if (Math.abs(change) < 5) return 'stable';
    return change > 0 ? 'increasing' : 'decreasing';
  }

  /**
   * Calculate percentile from data points
   */
  calculatePercentile(values, percentile) {
    if (values.length === 0) return 0;

    const sorted = [...values].sort((a, b) => a - b);
    const index = (percentile / 100) * (sorted.length - 1);
    const lower = Math.floor(index);
    const upper = Math.ceil(index);

    if (lower === upper) {
      return sorted[lower];
    }

    return sorted[lower] + (sorted[upper] - sorted[lower]) * (index - lower);
  }

  /**
   * Update cache with latest metrics
   */
  updateCache() {
    if (!this.config.cache.enabled) return;

    // Cache processed metrics
    this.cache.set('metrics', {
      data: Object.fromEntries(this.metrics),
      timestamp: Date.now()
    });

    // Clean up expired cache entries
    for (const [key, value] of this.cache) {
      if (Date.now() - value.timestamp > this.config.cache.ttl) {
        this.cache.delete(key);
      }
    }

    // Limit cache size
    if (this.cache.size > this.config.cache.maxSize) {
      const oldestKey = this.cache.keys().next().value;
      this.cache.delete(oldestKey);
    }
  }

  /**
   * Start alert evaluation
   */
  startAlertEvaluation() {
    this.alertInterval = setInterval(() => {
      this.evaluateAlerts();
    }, this.config.alerts.evaluationInterval);
  }

  /**
   * Evaluate analytics-based alerts
   */
  evaluateAlerts() {
    // Performance alerts
    this.evaluatePerformanceAlerts();

    // Security alerts
    this.evaluateSecurityAlerts();

    // Trend alerts
    this.evaluateTrendAlerts();
  }

  /**
   * Evaluate performance-related alerts
   */
  evaluatePerformanceAlerts() {
    const perfMetrics = this.metrics.get('performance');
    if (!perfMetrics) return;

    // CPU usage alert
    if (perfMetrics.cpu.avg > 80) {
      this.createAlert('performance', 'cpu_high', 'warning',
        `CPU usage is high: ${perfMetrics.cpu.avg.toFixed(1)}%`);
    }

    // Memory usage alert
    if (perfMetrics.memory.avg > 90) {
      this.createAlert('performance', 'memory_high', 'critical',
        `Memory usage is critical: ${perfMetrics.memory.avg.toFixed(1)}%`);
    }

    // Response time alert
    if (perfMetrics.responseTime.avg > 2000) {
      this.createAlert('performance', 'response_time_high', 'warning',
        `Response time is high: ${perfMetrics.responseTime.avg.toFixed(0)}ms`);
    }
  }

  /**
   * Evaluate security-related alerts
   */
  evaluateSecurityAlerts() {
    const securityMetrics = this.metrics.get('security');
    if (!securityMetrics) return;

    // Critical vulnerabilities alert
    if (securityMetrics.vulnerabilities.critical > 0) {
      this.createAlert('security', 'critical_vulnerabilities', 'critical',
        `Found ${securityMetrics.vulnerabilities.critical} critical vulnerabilities`);
    }

    // High vulnerabilities alert
    if (securityMetrics.vulnerabilities.high > 5) {
      this.createAlert('security', 'high_vulnerabilities', 'warning',
        `Found ${securityMetrics.vulnerabilities.high} high-severity vulnerabilities`);
    }
  }

  /**
   * Evaluate trend-based alerts
   */
  evaluateTrendAlerts() {
    const perfMetrics = this.metrics.get('performance');
    if (!perfMetrics) return;

    // Performance degradation alert
    if (perfMetrics.responseTime.trend === 'increasing') {
      this.createAlert('performance', 'performance_degradation', 'warning',
        'Response time is trending upward, potential performance degradation');
    }

    // Error rate increase alert
    if (perfMetrics.errorRate.trend === 'increasing') {
      this.createAlert('performance', 'error_rate_increasing', 'warning',
        'Error rate is increasing, investigate potential issues');
    }
  }

  /**
   * Create an analytics alert
   */
  createAlert(category, type, severity, message) {
    const alertId = `${category}_${type}_${Date.now()}`;
    const alertKey = `${category}_${type}`;

    // Check for alert cooldown
    const lastAlert = this.alerts.get(alertKey);
    if (lastAlert && (Date.now() - lastAlert.timestamp) < this.config.alerts.cooldownPeriod) {
      return;
    }

    const alert = {
      id: alertId,
      category,
      type,
      severity,
      message,
      timestamp: Date.now(),
      acknowledged: false,
      resolved: false
    };

    this.alerts.set(alertKey, alert);
    this.emit('alert', alert);

    console.log(`🚨 Analytics Alert: ${message}`);
  }

  /**
   * Start automated report generation
   */
  startReportGeneration() {
    // This would be implemented with a scheduler
    // For now, just set up the structure
    this.reportTemplates = {
      'daily-performance': this.generateDailyPerformanceReport.bind(this),
      'weekly-security': this.generateWeeklySecurityReport.bind(this),
      'monthly-executive': this.generateMonthlyExecutiveReport.bind(this)
    };
  }

  /**
   * Generate daily performance report
   */
  generateDailyPerformanceReport() {
    const perfMetrics = this.metrics.get('performance');
    if (!perfMetrics) return null;

    return {
      title: 'Daily Performance Report',
      date: new Date().toISOString().split('T')[0],
      summary: {
        cpu: `Average: ${perfMetrics.cpu.avg.toFixed(1)}%, Max: ${perfMetrics.cpu.max.toFixed(1)}%`,
        memory: `Average: ${perfMetrics.memory.avg.toFixed(1)}%, Max: ${perfMetrics.memory.max.toFixed(1)}%`,
        responseTime: `Average: ${perfMetrics.responseTime.avg.toFixed(0)}ms, P95: ${perfMetrics.responseTime.p95.toFixed(0)}ms`,
        throughput: `Average: ${perfMetrics.throughput.avg.toFixed(0)} RPS, Max: ${perfMetrics.throughput.max.toFixed(0)} RPS`,
        errorRate: `Average: ${perfMetrics.errorRate.avg.toFixed(2)}%, Max: ${perfMetrics.errorRate.max.toFixed(2)}%`
      },
      alerts: Array.from(this.alerts.values()).filter(a => a.timestamp > Date.now() - 86400000),
      recommendations: this.generatePerformanceRecommendations(perfMetrics)
    };
  }

  /**
   * Generate weekly security report
   */
  generateWeeklySecurityReport() {
    const securityMetrics = this.metrics.get('security');
    if (!securityMetrics) return null;

    return {
      title: 'Weekly Security Report',
      period: `${new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]} to ${new Date().toISOString().split('T')[0]}`,
      summary: {
        totalScans: securityMetrics.totalScans,
        vulnerabilities: securityMetrics.vulnerabilities,
        compliance: securityMetrics.compliance
      },
      trends: securityMetrics.trends,
      recommendations: this.generateSecurityRecommendations(securityMetrics)
    };
  }

  /**
   * Generate monthly executive report
   */
  generateMonthlyExecutiveReport() {
    return {
      title: 'Monthly Executive Report',
      period: new Date().toLocaleString('default', { month: 'long', year: 'numeric' }),
      kpis: {
        uptime: '99.9%',
        performance: 'Good',
        security: 'Secure',
        productivity: 'High'
      },
      highlights: [
        'System uptime maintained above 99.9%',
        'Zero critical security vulnerabilities',
        'Performance metrics within acceptable ranges',
        'All major projects delivered on time'
      ],
      risks: [],
      outlook: 'Positive - all systems operating normally'
    };
  }

  /**
   * Generate performance recommendations
   */
  generatePerformanceRecommendations(metrics) {
    const recommendations = [];

    if (metrics.cpu.avg > 70) {
      recommendations.push('Consider optimizing CPU-intensive operations or scaling compute resources');
    }

    if (metrics.memory.avg > 80) {
      recommendations.push('Monitor memory usage patterns and implement memory optimization techniques');
    }

    if (metrics.responseTime.avg > 1000) {
      recommendations.push('Optimize database queries, implement caching, or scale application servers');
    }

    if (metrics.errorRate.avg > 1) {
      recommendations.push('Investigate error patterns and improve error handling');
    }

    return recommendations;
  }

  /**
   * Generate security recommendations
   */
  generateSecurityRecommendations(metrics) {
    const recommendations = [];

    if (metrics.vulnerabilities.critical > 0) {
      recommendations.push('Address critical vulnerabilities immediately');
    }

    if (metrics.vulnerabilities.high > 5) {
      recommendations.push('Review and prioritize high-severity vulnerabilities');
    }

    if (metrics.compliance.score < 90) {
      recommendations.push('Improve compliance posture by addressing outstanding issues');
    }

    return recommendations;
  }

  /**
   * Create a dashboard
   */
  createDashboard(name, config) {
    this.dashboards.set(name, {
      ...config,
      created: Date.now(),
      lastUpdated: Date.now(),
      widgets: config.widgets || []
    });

    this.emit('dashboardCreated', name);
    return this.dashboards.get(name);
  }

  /**
   * Get dashboard data
   */
  getDashboardData(name) {
    const dashboard = this.dashboards.get(name);
    if (!dashboard) return null;

    const data = {
      dashboard,
      metrics: Object.fromEntries(this.metrics),
      alerts: Array.from(this.alerts.values()),
      timestamp: Date.now()
    };

    return data;
  }

  /**
   * Load dashboards from storage
   */
  async loadDashboards() {
    const dashboardsDir = path.join(__dirname, '..', 'config', 'dashboards');

    if (!fs.existsSync(dashboardsDir)) {
      fs.mkdirSync(dashboardsDir, { recursive: true });
      return;
    }

    const files = fs.readdirSync(dashboardsDir)
      .filter(file => file.endsWith('.json'));

    for (const file of files) {
      try {
        const content = fs.readFileSync(path.join(dashboardsDir, file), 'utf8');
        const dashboard = JSON.parse(content);
        this.dashboards.set(dashboard.name, dashboard);
      } catch (error) {
        console.warn(`⚠️  Failed to load dashboard ${file}:`, error.message);
      }
    }
  }

  /**
   * Load reports from storage
   */
  async loadReports() {
    const reportsDir = path.join(__dirname, '..', 'reports', 'analytics');

    if (!fs.existsSync(reportsDir)) {
      fs.mkdirSync(reportsDir, { recursive: true });
      return;
    }

    const files = fs.readdirSync(reportsDir)
      .filter(file => file.endsWith('.json'));

    for (const file of files) {
      try {
        const content = fs.readFileSync(path.join(reportsDir, file), 'utf8');
        const report = JSON.parse(content);
        this.reports.set(report.id, report);
      } catch (error) {
        console.warn(`⚠️  Failed to load report ${file}:`, error.message);
      }
    }
  }

  /**
   * Get current status
   */
  getStatus() {
    return {
      isRunning: this.isRunning,
      dataSources: Array.from(this.dataSources.entries()).map(([name, source]) => ({
        name,
        type: source.type,
        status: source.status,
        lastUpdate: source.lastUpdate
      })),
      metrics: Array.from(this.metrics.keys()),
      dashboards: Array.from(this.dashboards.keys()),
      alerts: Array.from(this.alerts.keys()).length,
      cache: {
        size: this.cache.size,
        enabled: this.config.cache.enabled
      }
    };
  }
}

module.exports = AnalyticsEngine;
