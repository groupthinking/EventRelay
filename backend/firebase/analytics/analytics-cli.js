#!/usr/bin/env node

/**
 * Analytics Engine CLI
 * Command-line interface for analytics operations
 */

const AnalyticsEngine = require('./analytics-engine');

class AnalyticsCLI {
  constructor() {
    this.engine = new AnalyticsEngine();
    this.isRunning = false;
  }

  async run() {
    const command = process.argv[2];
    const args = process.argv.slice(3);

    try {
      switch (command) {
        case 'start':
          await this.startEngine();
          break;
        case 'stop':
          await this.stopEngine();
          break;
        case 'status':
          await this.showStatus();
          break;
        case 'dashboard':
          await this.showDashboard(args);
          break;
        case 'metrics':
          await this.showMetrics(args);
          break;
        case 'report':
          await this.generateReport(args);
          break;
        case 'alerts':
          await this.showAlerts();
          break;
        case 'predict':
          await this.showPredictions();
          break;
        default:
          this.showHelp();
      }
    } catch (error) {
      console.error('❌ Error:', error.message);
      process.exit(1);
    }
  }

  async startEngine() {
    if (this.isRunning) {
      console.log('📊 Analytics engine is already running');
      return;
    }

    console.log('🚀 Starting analytics engine...');

    try {
      this.engine.on('started', () => {
        console.log('✅ Analytics engine started successfully');
        this.isRunning = true;
      });

      this.engine.on('dataCollected', (sources) => {
        console.log(`📊 Collected data from ${sources.length} sources`);
      });

      this.engine.on('metricsProcessed', (metricCount) => {
        console.log(`🔢 Processed ${metricCount} metrics`);
      });

      await this.engine.start();

      // Keep the process running
      process.on('SIGINT', async () => {
        console.log('\n🛑 Shutting down analytics engine...');
        await this.stopEngine();
        process.exit(0);
      });

      console.log('📊 Analytics engine running...');
      console.log('Press Ctrl+C to stop');

      // Keep alive
      setInterval(() => {}, 1000);
    } catch (error) {
      console.error('❌ Failed to start analytics engine:', error.message);
      process.exit(1);
    }
  }

  async stopEngine() {
    if (!this.isRunning) {
      console.log('📊 Analytics engine is not running');
      return;
    }

    try {
      await this.engine.stop();
      this.isRunning = false;
    } catch (error) {
      console.error('❌ Failed to stop analytics engine:', error.message);
    }
  }

  async showStatus() {
    const status = this.engine.getStatus();

    console.log('📊 Analytics Engine Status\n');

    console.log(`Status: ${status.isRunning ? '🟢 Running' : '🔴 Stopped'}`);
    console.log(`Data Sources: ${status.dataSources.length}`);
    console.log(`Metrics: ${status.metrics}`);
    console.log(`Dashboards: ${status.dashboards}`);
    console.log(`Active Alerts: ${status.alerts}`);

    if (status.dataSources.length > 0) {
      console.log('\n📡 Data Sources:');
      status.dataSources.forEach(source => {
        console.log(`  ${source.name}: ${source.status} (${source.lastUpdate ? new Date(source.lastUpdate).toLocaleString() : 'Never'})`);
      });
    }
  }

  async showDashboard(args) {
    const [dashboardName] = args;

    if (!dashboardName) {
      console.log('Available dashboards:');
      const status = this.engine.getStatus();
      status.dashboards.forEach(name => console.log(`  ${name}`));
      return;
    }

    const data = this.engine.getDashboardData(dashboardName);

    if (!data) {
      console.log(`❌ Dashboard '${dashboardName}' not found`);
      return;
    }

    console.log(`📊 ${dashboardName} Dashboard\n`);

    // Display metrics summary
    console.log('📈 Key Metrics:');
    Object.entries(data.metrics).forEach(([source, metrics]) => {
      console.log(`\n🔧 ${source.toUpperCase()}:`);
      if (metrics.cpu) {
        console.log(`  CPU: ${metrics.cpu.avg?.toFixed(1)}% (Max: ${metrics.cpu.max?.toFixed(1)}%)`);
      }
      if (metrics.memory) {
        console.log(`  Memory: ${metrics.memory.avg?.toFixed(1)}% (Max: ${metrics.memory.max?.toFixed(1)}%)`);
      }
      if (metrics.responseTime) {
        console.log(`  Response Time: ${metrics.responseTime.avg?.toFixed(0)}ms (P95: ${metrics.responseTime.p95?.toFixed(0)}ms)`);
      }
      if (metrics.errorRate) {
        console.log(`  Error Rate: ${metrics.errorRate.avg?.toFixed(2)}%`);
      }
    });
  }

  async showMetrics(args) {
    const [source] = args;
    const status = this.engine.getStatus();

    if (!source) {
      console.log('Available metric sources:');
      Object.keys(status.metrics).forEach(src => console.log(`  ${src}`));
      return;
    }

    const metrics = this.engine.metrics.get(source);
    if (!metrics) {
      console.log(`❌ No metrics found for source: ${source}`);
      return;
    }

    console.log(`📊 ${source.toUpperCase()} Metrics\n`);

    this.displayMetrics(metrics);
  }

  displayMetrics(metrics) {
    Object.entries(metrics).forEach(([category, data]) => {
      console.log(`${category.toUpperCase()}:`);
      if (typeof data === 'object') {
        Object.entries(data).forEach(([key, value]) => {
          if (typeof value === 'number') {
            console.log(`  ${key}: ${value.toFixed ? value.toFixed(2) : value}`);
          } else if (typeof value === 'string') {
            console.log(`  ${key}: ${value}`);
          }
        });
      }
      console.log('');
    });
  }

  async generateReport(args) {
    const [format] = args || ['console'];

    console.log('📝 Generating analytics report...');

    try {
      const report = await this.engine.generateReport();

      switch (format.toLowerCase()) {
        case 'json':
          console.log(JSON.stringify(report, null, 2));
          break;
        case 'html':
          await this.generateHtmlReport(report);
          break;
        default:
          this.displayReportSummary(report);
      }
    } catch (error) {
      console.error('❌ Failed to generate report:', error.message);
    }
  }

  displayReportSummary(report) {
    console.log('📊 Analytics Report Summary\n');

    console.log(`Report Period: ${report.period}`);
    console.log(`Generated: ${new Date(report.timestamp).toLocaleString()}\n`);

    console.log('📈 Summary Statistics:');
    console.log(`  Total Metrics: ${Object.keys(report.summary).length}`);
    console.log(`  Data Sources: ${Object.keys(report.metrics).length}`);

    if (report.trends) {
      console.log('\n📉 Key Trends:');
      Object.entries(report.trends).forEach(([metric, trend]) => {
        console.log(`  ${metric}: ${trend.direction} (${trend.change?.toFixed(1) || 0}%)`);
      });
    }

    if (report.recommendations && report.recommendations.length > 0) {
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
  <title>Analytics Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    .header { background: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
    .metric { display: inline-block; margin: 10px; padding: 15px; background: #e3f2fd; border-radius: 5px; }
    .metric-value { font-size: 24px; font-weight: bold; }
    .trend { margin: 10px 0; padding: 10px; border-radius: 5px; }
    .increasing { background: #ffebee; border: 1px solid #f44336; }
    .decreasing { background: #e8f5e8; border: 1px solid #4caf50; }
    .stable { background: #fff3e0; border: 1px solid #ff9800; }
    .recommendations { background: #f3e5f5; padding: 15px; border-radius: 5px; margin-top: 20px; }
  </style>
</head>
<body>
  <div class="header">
    <h1>📊 Analytics Report</h1>
    <p><strong>Generated:</strong> ${new Date(report.timestamp).toLocaleString()}</p>
    <p><strong>Period:</strong> ${report.period}</p>
  </div>

  <h2>📈 Key Metrics</h2>
  ${Object.entries(report.summary).map(([key, value]) => `
    <div class="metric">
      <div class="metric-value">${value}</div>
      <div>${key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}</div>
    </div>
  `).join('')}

  ${report.trends ? `
    <h2>📉 Trends</h2>
    ${Object.entries(report.trends).map(([metric, trend]) => `
      <div class="trend ${trend.direction}">
        <strong>${metric}:</strong> ${trend.direction} (${trend.change?.toFixed(1) || 0}%)
      </div>
    `).join('')}
  ` : ''}

  ${report.recommendations ? `
    <div class="recommendations">
      <h2>💡 Recommendations</h2>
      <ul>
      ${report.recommendations.map(rec => `<li>${rec}</li>`).join('')}
      </ul>
    </div>
  ` : ''}
</body>
</html>`;

    const reportPath = path.join(__dirname, '..', 'reports', 'analytics', `analytics-report-${Date.now()}.html`);
    const fs = require('fs');
    const dir = path.dirname(reportPath);

    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    fs.writeFileSync(reportPath, html);
    console.log(`✅ HTML report saved to ${reportPath}`);
  }

  async showAlerts() {
    console.log('🚨 Active Analytics Alerts\n');

    // This would show alerts from the analytics engine
    // For now, show placeholder
    console.log('No active alerts at this time.');
  }

  async showPredictions() {
    console.log('🔮 Risk Predictions\n');

    // This would show predictions from the analytics engine
    // For now, show placeholder
    console.log('No predictions available at this time.');
    console.log('Run the analytics engine to generate predictions.');
  }

  showHelp() {
    console.log('📊 Analytics Engine CLI\n');
    console.log('Usage: npm run analytics <command> [options]\n');
    console.log('Commands:');
    console.log('  start          Start the analytics engine');
    console.log('  stop           Stop the analytics engine');
    console.log('  status         Show engine status');
    console.log('  dashboard <id> Show dashboard data');
    console.log('  metrics <src>  Show metrics for source');
    console.log('  report [fmt]   Generate analytics report');
    console.log('  alerts         Show active alerts');
    console.log('  predict        Show risk predictions');
    console.log('');
    console.log('Examples:');
    console.log('  npm run analytics start');
    console.log('  npm run analytics dashboard performance');
    console.log('  npm run analytics metrics performance');
    console.log('  npm run analytics report html');
    console.log('');
    console.log('For more help, run: npm run analytics help');
  }
}

// Run CLI if called directly
if (require.main === module) {
  const cli = new AnalyticsCLI();
  cli.run().catch(error => {
    console.error('CLI Error:', error.message);
    process.exit(1);
  });
}

module.exports = AnalyticsCLI;
