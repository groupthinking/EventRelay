#!/usr/bin/env node

/**
 * Performance Monitoring CLI
 * Command-line interface for managing performance monitoring
 */

const PerformanceMonitor = require('./performance-monitor');
const fs = require('fs');
const path = require('path');

class MonitoringCLI {
  constructor() {
    this.monitor = new PerformanceMonitor();
    this.isRunning = false;
  }

  async run() {
    const command = process.argv[2];
    const args = process.argv.slice(3);

    try {
      switch (command) {
        case 'start':
          await this.startMonitoring();
          break;
        case 'stop':
          await this.stopMonitoring();
          break;
        case 'status':
          await this.showStatus();
          break;
        case 'metrics':
          await this.showMetrics(args);
          break;
        case 'alerts':
          await this.showAlerts(args);
          break;
        case 'report':
          await this.generateReport(args);
          break;
        case 'baseline':
          await this.manageBaseline(args);
          break;
        case 'config':
          await this.showConfig();
          break;
        case 'test':
          await this.testAlerts();
          break;
        default:
          this.showHelp();
      }
    } catch (error) {
      console.error('❌ Error:', error.message);
      process.exit(1);
    }
  }

  async startMonitoring() {
    if (this.isRunning) {
      console.log('📊 Monitoring is already running');
      return;
    }

    console.log('🚀 Starting performance monitoring...');

    try {
      this.monitor.on('started', () => {
        console.log('✅ Performance monitoring started successfully');
        this.isRunning = true;
      });

      this.monitor.on('stopped', () => {
        console.log('🛑 Performance monitoring stopped');
        this.isRunning = false;
      });

      this.monitor.on('alert', (alert) => {
        console.log(`🚨 ALERT: ${alert.message}`);
      });

      await this.monitor.start();

      // Keep the process running
      process.on('SIGINT', async () => {
        console.log('\n🛑 Shutting down monitoring...');
        await this.stopMonitoring();
        process.exit(0);
      });

      console.log('📊 Monitoring metrics every 30 seconds...');
      console.log('Press Ctrl+C to stop');

      // Keep alive
      setInterval(() => {}, 1000);
    } catch (error) {
      console.error('❌ Failed to start monitoring:', error.message);
      process.exit(1);
    }
  }

  async stopMonitoring() {
    if (!this.isRunning) {
      console.log('📊 Monitoring is not running');
      return;
    }

    try {
      await this.monitor.stop();
      this.isRunning = false;
    } catch (error) {
      console.error('❌ Failed to stop monitoring:', error.message);
    }
  }

  async showStatus() {
    const status = this.monitor.getStatus();

    console.log('📊 Performance Monitoring Status\n');

    console.log(`Status: ${status.isMonitoring ? '🟢 Running' : '🔴 Stopped'}`);
    if (status.uptime > 0) {
      const uptimeMinutes = Math.floor(status.uptime / 60000);
      console.log(`Uptime: ${uptimeMinutes} minutes`);
    }

    console.log('\n📈 Current Metrics:');

    // System metrics
    console.log('\n🔧 System:');
    console.log(`  CPU: ${status.metrics.system.cpu.usage.toFixed(1)}%`);
    console.log(`  Memory: ${status.metrics.system.memory.usage.toFixed(1)}%`);
    console.log(`  Disk: ${status.metrics.system.disk.usage.toFixed(1)}%`);

    // Application metrics
    console.log('\n📱 Application:');
    console.log(`  Response Time: ${status.metrics.app.responseTime.avg.toFixed(0)}ms`);
    console.log(`  Throughput: ${status.metrics.app.throughput.rps} RPS`);
    console.log(`  Error Rate: ${status.metrics.app.errorRate.percentage.toFixed(2)}%`);
    console.log(`  Active Connections: ${status.metrics.app.activeConnections.count}`);

    console.log('\n🚨 Active Alerts:');
    if (status.alerts.length === 0) {
      console.log('  No active alerts');
    } else {
      status.alerts.forEach(alert => {
        console.log(`  ${alert.severity.toUpperCase()}: ${alert.metric} - ${alert.message}`);
      });
    }
  }

  async showMetrics(args) {
    const [metricType, timeRange] = args;
    const status = this.monitor.getStatus();

    console.log('📊 Detailed Metrics\n');

    switch (metricType) {
      case 'system':
      case 'cpu':
        this.displayMetricHistory('CPU Usage', status.metrics.system.cpu.history);
        break;
      case 'memory':
        this.displayMetricHistory('Memory Usage', status.metrics.system.memory.history);
        break;
      case 'response':
        this.displayMetricHistory('Response Time', status.metrics.app.responseTime.history);
        break;
      case 'throughput':
        this.displayMetricHistory('Throughput', status.metrics.app.throughput.history);
        break;
      case 'errors':
        this.displayMetricHistory('Error Rate', status.metrics.app.errorRate.history);
        break;
      default:
        console.log('Available metrics:');
        console.log('  system  - System metrics (CPU, Memory, Disk)');
        console.log('  cpu     - CPU usage history');
        console.log('  memory  - Memory usage history');
        console.log('  response - Response time history');
        console.log('  throughput - Throughput history');
        console.log('  errors  - Error rate history');
    }
  }

  displayMetricHistory(title, history) {
    console.log(`${title}:`);
    console.log('─'.repeat(50));

    if (history.length === 0) {
      console.log('No data available');
      return;
    }

    const recent = history.slice(-10); // Show last 10 entries
    recent.forEach(entry => {
      const time = new Date(entry.timestamp).toLocaleTimeString();
      console.log(`${time}: ${entry.value.toFixed(2)}`);
    });

    // Calculate statistics
    const values = recent.map(entry => entry.value);
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    const min = Math.min(...values);
    const max = Math.max(...values);

    console.log('─'.repeat(50));
    console.log(`Average: ${avg.toFixed(2)} | Min: ${min.toFixed(2)} | Max: ${max.toFixed(2)}`);
  }

  async showAlerts(args) {
    const [filter] = args;
    const status = this.monitor.getStatus();

    console.log('🚨 Performance Alerts\n');

    let alerts = status.alerts;

    if (filter) {
      alerts = alerts.filter(alert =>
        alert.severity === filter || alert.metric === filter
      );
    }

    if (alerts.length === 0) {
      console.log('No alerts found');
      return;
    }

    alerts.forEach(alert => {
      const time = new Date(alert.timestamp).toLocaleString();
      console.log(`[${alert.severity.toUpperCase()}] ${time}`);
      console.log(`  ${alert.metric}: ${alert.message}`);
      console.log(`  Current: ${alert.currentValue.toFixed(2)} | Threshold: ${alert.threshold}`);
      console.log('');
    });

    // Summary
    const bySeverity = alerts.reduce((acc, alert) => {
      acc[alert.severity] = (acc[alert.severity] || 0) + 1;
      return acc;
    }, {});

    console.log('📊 Alert Summary:');
    Object.entries(bySeverity).forEach(([severity, count]) => {
      console.log(`  ${severity}: ${count}`);
    });
  }

  async generateReport(args) {
    const [format] = args || ['json'];

    console.log(`📝 Generating performance report (${format})...`);

    try {
      const report = this.monitor.generateReport();

      switch (format.toLowerCase()) {
        case 'json':
          console.log(JSON.stringify(report, null, 2));
          break;
        case 'html':
          await this.generateHtmlReport(report);
          break;
        case 'summary':
          this.displayReportSummary(report);
          break;
        default:
          console.log('Available formats: json, html, summary');
      }
    } catch (error) {
      console.error('❌ Failed to generate report:', error.message);
    }
  }

  displayReportSummary(report) {
    console.log('📊 Performance Report Summary\n');

    console.log('Average Metrics (24h):');
    console.log(`  CPU: ${report.summary.averageCpu.toFixed(1)}%`);
    console.log(`  Memory: ${report.summary.averageMemory.toFixed(1)}%`);
    console.log(`  Response Time: ${report.summary.averageResponseTime.toFixed(0)}ms`);
    console.log(`  Throughput: ${report.summary.averageThroughput.toFixed(0)} RPS`);
    console.log(`  Error Rate: ${report.summary.averageErrorRate.toFixed(2)}%`);

    console.log(`\nTotal Alerts: ${report.summary.totalAlerts}`);

    if (report.trends.cpu) {
      console.log('\n📈 Trends:');
      console.log(`  CPU: ${report.trends.cpu.direction} (${report.trends.cpu.change.toFixed(1)}%)`);
    }

    if (report.recommendations.length > 0) {
      console.log('\n💡 Recommendations:');
      report.recommendations.forEach(rec => {
        console.log(`  • ${rec}`);
      });
    }
  }

  async generateHtmlReport(report) {
    const html = `
<!DOCTYPE html>
<html>
<head>
  <title>Performance Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    .header { background: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
    .metric { display: inline-block; margin: 10px; padding: 15px; background: #e3f2fd; border-radius: 5px; }
    .metric-value { font-size: 24px; font-weight: bold; }
    .recommendations { background: #f3e5f5; padding: 15px; border-radius: 5px; margin-top: 20px; }
    table { width: 100%; border-collapse: collapse; margin: 10px 0; }
    th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
    th { background-color: #f8f9fa; }
  </style>
</head>
<body>
  <div class="header">
    <h1>📊 Performance Report</h1>
    <p><strong>Generated:</strong> ${new Date(report.timestamp).toLocaleString()}</p>
    <p><strong>Period:</strong> ${report.period}</p>
  </div>

  <h2>📈 Average Metrics</h2>
  <div class="metric">
    <div class="metric-value">${report.summary.averageCpu.toFixed(1)}%</div>
    <div>CPU Usage</div>
  </div>
  <div class="metric">
    <div class="metric-value">${report.summary.averageMemory.toFixed(1)}%</div>
    <div>Memory Usage</div>
  </div>
  <div class="metric">
    <div class="metric-value">${report.summary.averageResponseTime.toFixed(0)}ms</div>
    <div>Response Time</div>
  </div>
  <div class="metric">
    <div class="metric-value">${report.summary.averageThroughput.toFixed(0)}</div>
    <div>Throughput (RPS)</div>
  </div>
  <div class="metric">
    <div class="metric-value">${report.summary.averageErrorRate.toFixed(2)}%</div>
    <div>Error Rate</div>
  </div>

  <div class="recommendations">
    <h2>💡 Recommendations</h2>
    <ul>
    ${report.recommendations.map(rec => `<li>${rec}</li>`).join('')}
    </ul>
  </div>
</body>
</html>`;

    const reportPath = path.join(__dirname, '..', 'monitoring', 'reports', `performance-report-${Date.now()}.html`);
    fs.writeFileSync(reportPath, html);
    console.log(`✅ HTML report saved to ${reportPath}`);
  }

  async manageBaseline(args) {
    const [action] = args;

    switch (action) {
      case 'set':
        await this.setBaseline();
        break;
      case 'reset':
        await this.resetBaseline();
        break;
      case 'show':
        await this.showBaseline();
        break;
      default:
        console.log('Baseline commands:');
        console.log('  set   - Set current metrics as baseline');
        console.log('  reset - Reset to default baseline');
        console.log('  show  - Show current baseline values');
    }
  }

  async setBaseline() {
    console.log('📊 Setting current metrics as baseline...');

    const status = this.monitor.getStatus();
    const baseline = {
      cpu: { warning: status.metrics.system.cpu.usage + 10, critical: status.metrics.system.cpu.usage + 20 },
      memory: { warning: status.metrics.system.memory.usage + 5, critical: status.metrics.system.memory.usage + 10 },
      responseTime: { warning: status.metrics.app.responseTime.avg * 1.2, critical: status.metrics.app.responseTime.avg * 1.5 },
      errorRate: { warning: status.metrics.app.errorRate.percentage * 1.5, critical: status.metrics.app.errorRate.percentage * 2 },
      throughput: { min: status.metrics.app.throughput.rps * 0.8, max: status.metrics.app.throughput.rps * 1.5 }
    };

    this.monitor.baselines = baseline;
    this.monitor.saveBaselines();

    console.log('✅ Baseline updated successfully');
    this.showBaseline();
  }

  async resetBaseline() {
    console.log('🔄 Resetting to default baseline...');
    this.monitor.baselines = {};
    await this.monitor.loadBaselines();
    console.log('✅ Baseline reset to defaults');
  }

  async showBaseline() {
    console.log('📊 Current Baseline Values\n');

    const baselines = this.monitor.baselines;

    Object.entries(baselines).forEach(([metric, thresholds]) => {
      console.log(`${metric.toUpperCase()}:`);
      if (typeof thresholds === 'object') {
        Object.entries(thresholds).forEach(([level, value]) => {
          console.log(`  ${level}: ${value}`);
        });
      }
      console.log('');
    });
  }

  async showConfig() {
    console.log('⚙️  Performance Monitoring Configuration\n');

    const config = this.monitor.config;

    console.log(`Enabled: ${config.enabled ? '✅' : '❌'}`);
    console.log(`Collection Interval: ${config.collection.interval / 1000} seconds`);
    console.log(`Retention Period: ${config.collection.retentionPeriod / (24 * 60 * 60 * 1000)} days`);

    console.log('\n📊 Thresholds:');
    Object.entries(config.thresholds).forEach(([metric, thresholds]) => {
      if (typeof thresholds === 'object' && thresholds.warning) {
        console.log(`  ${metric}: Warning ${thresholds.warning}, Critical ${thresholds.critical}`);
      }
    });

    console.log('\n🚨 Alert Channels:');
    Object.entries(config.alerts.channels).forEach(([channel, settings]) => {
      console.log(`  ${channel}: ${settings.enabled ? '✅' : '❌'}`);
    });
  }

  async testAlerts() {
    console.log('🧪 Testing alert system...');

    // Simulate high CPU usage
    this.monitor.systemMetrics.cpu.usage = 95;
    this.monitor.checkThresholds();

    // Simulate high response time
    this.monitor.appMetrics.responseTime.avg = 2500;
    this.monitor.checkThresholds();

    console.log('✅ Alert test completed - check console for alert messages');
  }

  showHelp() {
    console.log('📊 Performance Monitoring CLI\n');
    console.log('Usage: npm run monitoring <command> [options]\n');
    console.log('Commands:');
    console.log('  start          Start performance monitoring');
    console.log('  stop           Stop performance monitoring');
    console.log('  status         Show current monitoring status');
    console.log('  metrics <type> Show detailed metrics history');
    console.log('  alerts [filter] Show active alerts');
    console.log('  report [format] Generate performance report');
    console.log('  baseline <cmd> Manage performance baselines');
    console.log('  config         Show current configuration');
    console.log('  test           Test alert system');
    console.log('');
    console.log('Examples:');
    console.log('  npm run monitoring start');
    console.log('  npm run monitoring metrics cpu');
    console.log('  npm run monitoring alerts critical');
    console.log('  npm run monitoring report html');
    console.log('  npm run monitoring baseline set');
    console.log('');
    console.log('For more help, run: npm run monitoring help');
  }
}

// Run CLI if called directly
if (require.main === module) {
  const cli = new MonitoringCLI();
  cli.run().catch(error => {
    console.error('CLI Error:', error.message);
    process.exit(1);
  });
}

module.exports = MonitoringCLI;
