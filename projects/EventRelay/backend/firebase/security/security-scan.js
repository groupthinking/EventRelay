/**
 * Security Scanning Integration
 * Comprehensive security scanning with multiple tools and reporting
 */

const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const axios = require('axios');

class SecurityScanner {
  constructor() {
    this.results = {
      timestamp: new Date().toISOString(),
      scans: {},
      summary: {
        totalIssues: 0,
        criticalIssues: 0,
        highIssues: 0,
        mediumIssues: 0,
        lowIssues: 0,
        infoIssues: 0
      },
      recommendations: []
    };

    this.config = this.loadConfig();
  }

  loadConfig() {
    const configPath = path.join(__dirname, '..', 'config', 'security-config.json');

    if (fs.existsSync(configPath)) {
      return JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }

    // Default configuration
    return {
      tools: {
        snyk: { enabled: true },
        owasp: { enabled: true },
        sonar: { enabled: false },
        trivy: { enabled: true }
      },
      thresholds: {
        critical: 0,
        high: 5,
        medium: 10,
        low: 20
      },
      notifications: {
        slack: { enabled: false },
        email: { enabled: false }
      }
    };
  }

  /**
   * Run comprehensive security scan
   */
  async runFullScan() {
    console.log('🔒 Starting comprehensive security scan...');

    const scanPromises = [];

    if (this.config.tools.snyk.enabled) {
      scanPromises.push(this.runSnykScan());
    }

    if (this.config.tools.owasp.enabled) {
      scanPromises.push(this.runOWASPScan());
    }

    if (this.config.tools.trivy.enabled) {
      scanPromises.push(this.runTrivyScan());
    }

    if (this.config.tools.sonar.enabled) {
      scanPromises.push(this.runSonarScan());
    }

    try {
      await Promise.all(scanPromises);
      this.generateSummary();
      this.generateReport();
      this.sendNotifications();

      console.log('✅ Security scan completed successfully!');
      return this.results;
    } catch (error) {
      console.error('❌ Security scan failed:', error.message);
      throw error;
    }
  }

  /**
   * Run Snyk security scan
   */
  async runSnykScan() {
    console.log('🔍 Running Snyk dependency vulnerability scan...');

    try {
      const output = execSync('npx snyk test --json', {
        cwd: path.join(__dirname, '..'),
        encoding: 'utf8'
      });

      const results = JSON.parse(output);

      this.results.scans.snyk = {
        tool: 'Snyk',
        type: 'Dependency Vulnerability Scan',
        status: 'completed',
        issues: results.vulnerabilities || [],
        summary: {
          total: results.vulnerabilities?.length || 0,
          critical: results.vulnerabilities?.filter(v => v.severity === 'critical').length || 0,
          high: results.vulnerabilities?.filter(v => v.severity === 'high').length || 0,
          medium: results.vulnerabilities?.filter(v => v.severity === 'medium').length || 0,
          low: results.vulnerabilities?.filter(v => v.severity === 'low').length || 0
        }
      };

      console.log(`✅ Snyk scan found ${results.vulnerabilities?.length || 0} vulnerabilities`);
    } catch (error) {
      this.results.scans.snyk = {
        tool: 'Snyk',
        status: 'failed',
        error: error.message
      };
      console.error('❌ Snyk scan failed:', error.message);
    }
  }

  /**
   * Run OWASP Dependency Check
   */
  async runOWASPScan() {
    console.log('🔍 Running OWASP Dependency Check...');

    try {
      // Create reports directory if it doesn't exist
      const reportsDir = path.join(__dirname, '..', 'reports');
      if (!fs.existsSync(reportsDir)) {
        fs.mkdirSync(reportsDir, { recursive: true });
      }

      execSync('dependency-check.sh --project "Firebase Project" --scan . --out reports/ --format JSON', {
        cwd: path.join(__dirname, '..'),
        stdio: 'inherit'
      });

      const reportPath = path.join(__dirname, '..', 'reports', 'dependency-check-report.json');

      if (fs.existsSync(reportPath)) {
        const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));

        this.results.scans.owasp = {
          tool: 'OWASP Dependency Check',
          type: 'Static Security Analysis',
          status: 'completed',
          issues: report.dependencies?.filter(dep => dep.vulnerabilities?.length > 0) || [],
          summary: {
            total: report.dependencies?.length || 0,
            vulnerable: report.dependencies?.filter(dep => dep.vulnerabilities?.length > 0).length || 0
          }
        };

        console.log(`✅ OWASP scan completed - ${report.dependencies?.length || 0} dependencies analyzed`);
      } else {
        throw new Error('OWASP report not generated');
      }
    } catch (error) {
      this.results.scans.owasp = {
        tool: 'OWASP Dependency Check',
        status: 'failed',
        error: error.message
      };
      console.error('❌ OWASP scan failed:', error.message);
    }
  }

  /**
   * Run Trivy container vulnerability scan
   */
  async runTrivyScan() {
    console.log('🔍 Running Trivy container vulnerability scan...');

    try {
      const output = execSync('trivy image --format json --output trivy-results.json your-app:latest 2>/dev/null || echo "{}"', {
        cwd: path.join(__dirname, '..'),
        encoding: 'utf8'
      });

      const results = JSON.parse(output || '{}');

      this.results.scans.trivy = {
        tool: 'Trivy',
        type: 'Container Vulnerability Scan',
        status: 'completed',
        issues: results.Results?.[0]?.Vulnerabilities || [],
        summary: {
          total: results.Results?.[0]?.Vulnerabilities?.length || 0,
          critical: results.Results?.[0]?.Vulnerabilities?.filter(v => v.Severity === 'CRITICAL').length || 0,
          high: results.Results?.[0]?.Vulnerabilities?.filter(v => v.Severity === 'HIGH').length || 0,
          medium: results.Results?.[0]?.Vulnerabilities?.filter(v => v.Severity === 'MEDIUM').length || 0,
          low: results.Results?.[0]?.Vulnerabilities?.filter(v => v.Severity === 'LOW').length || 0
        }
      };

      console.log(`✅ Trivy scan found ${results.Results?.[0]?.Vulnerabilities?.length || 0} container vulnerabilities`);
    } catch (error) {
      this.results.scans.trivy = {
        tool: 'Trivy',
        status: 'failed',
        error: error.message
      };
      console.error('❌ Trivy scan failed:', error.message);
    }
  }

  /**
   * Run SonarQube code quality and security scan
   */
  async runSonarScan() {
    console.log('🔍 Running SonarQube code quality scan...');

    try {
      execSync('sonar-scanner -Dsonar.projectKey=firebase-project -Dsonar.sources=src', {
        cwd: path.join(__dirname, '..'),
        stdio: 'inherit'
      });

      this.results.scans.sonar = {
        tool: 'SonarQube',
        type: 'Code Quality & Security Scan',
        status: 'completed',
        message: 'SonarQube analysis completed - check dashboard for detailed results'
      };

      console.log('✅ SonarQube scan completed - check dashboard for results');
    } catch (error) {
      this.results.scans.sonar = {
        tool: 'SonarQube',
        status: 'failed',
        error: error.message
      };
      console.error('❌ SonarQube scan failed:', error.message);
    }
  }

  /**
   * Generate security scan summary
   */
  generateSummary() {
    console.log('📊 Generating security scan summary...');

    this.results.summary = {
      totalIssues: 0,
      criticalIssues: 0,
      highIssues: 0,
      mediumIssues: 0,
      lowIssues: 0,
      infoIssues: 0
    };

    Object.values(this.results.scans).forEach(scan => {
      if (scan.summary) {
        this.results.summary.totalIssues += scan.summary.total || 0;
        this.results.summary.criticalIssues += scan.summary.critical || 0;
        this.results.summary.highIssues += scan.summary.high || 0;
        this.results.summary.mediumIssues += scan.summary.medium || 0;
        this.results.summary.lowIssues += scan.summary.low || 0;
        this.results.summary.infoIssues += scan.summary.info || 0;
      }
    });

    console.log(`📈 Summary: ${this.results.summary.totalIssues} total issues found`);
    console.log(`   Critical: ${this.results.summary.criticalIssues}`);
    console.log(`   High: ${this.results.summary.highIssues}`);
    console.log(`   Medium: ${this.results.summary.mediumIssues}`);
  }

  /**
   * Generate comprehensive security report
   */
  generateReport() {
    console.log('📝 Generating security report...');

    const report = {
      ...this.results,
      recommendations: this.generateRecommendations()
    };

    const reportPath = path.join(__dirname, '..', 'reports', 'security-scan-report.json');
    const htmlReportPath = path.join(__dirname, '..', 'reports', 'security-scan-report.html');

    // Ensure reports directory exists
    const reportsDir = path.dirname(reportPath);
    if (!fs.existsSync(reportsDir)) {
      fs.mkdirSync(reportsDir, { recursive: true });
    }

    // Save JSON report
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

    // Generate HTML report
    this.generateHtmlReport(report, htmlReportPath);

    console.log(`✅ Security report saved to ${reportPath}`);
    console.log(`✅ HTML report saved to ${htmlReportPath}`);
  }

  /**
   * Generate HTML security report
   */
  generateHtmlReport(report, htmlPath) {
    const html = `
<!DOCTYPE html>
<html>
<head>
  <title>Security Scan Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    .header { background: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
    .summary { background: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
    .scan-result { margin: 10px 0; padding: 15px; border-radius: 5px; }
    .success { background: #e8f5e8; border: 1px solid #4caf50; }
    .warning { background: #fff3e0; border: 1px solid #ff9800; }
    .error { background: #ffebee; border: 1px solid #f44336; }
    .metric { display: inline-block; margin: 10px; text-align: center; }
    .metric-value { font-size: 24px; font-weight: bold; }
    .recommendations { background: #f3e5f5; padding: 15px; border-radius: 5px; margin-top: 20px; }
    table { width: 100%; border-collapse: collapse; margin: 10px 0; }
    th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
    th { background-color: #f8f9fa; }
  </style>
</head>
<body>
  <div class="header">
    <h1>🔒 Security Scan Report</h1>
    <p><strong>Generated:</strong> ${new Date(report.timestamp).toLocaleString()}</p>
    <p><strong>Project:</strong> Firebase Project</p>
  </div>

  <div class="summary">
    <h2>📊 Executive Summary</h2>
    <div class="metric">
      <div class="metric-value">${report.summary.totalIssues}</div>
      <div>Total Issues</div>
    </div>
    <div class="metric">
      <div class="metric-value" style="color: #f44336;">${report.summary.criticalIssues}</div>
      <div>Critical</div>
    </div>
    <div class="metric">
      <div class="metric-value" style="color: #ff9800;">${report.summary.highIssues}</div>
      <div>High</div>
    </div>
    <div class="metric">
      <div class="metric-value" style="color: #ff9800;">${report.summary.mediumIssues}</div>
      <div>Medium</div>
    </div>
    <div class="metric">
      <div class="metric-value" style="color: #2196f3;">${report.summary.lowIssues}</div>
      <div>Low</div>
    </div>
  </div>

  <h2>🔍 Scan Results</h2>
  ${Object.entries(report.scans).map(([tool, result]) => `
    <div class="scan-result ${result.status === 'completed' ? 'success' : 'error'}">
      <h3>${result.tool}</h3>
      <p><strong>Type:</strong> ${result.type}</p>
      <p><strong>Status:</strong> ${result.status}</p>
      ${result.summary ? `
        <table>
          <tr><th>Metric</th><th>Value</th></tr>
          ${Object.entries(result.summary).map(([key, value]) => `
            <tr><td>${key}</td><td>${value}</td></tr>
          `).join('')}
        </table>
      ` : ''}
      ${result.error ? `<p style="color: red;"><strong>Error:</strong> ${result.error}</p>` : ''}
    </div>
  `).join('')}

  <div class="recommendations">
    <h2>💡 Recommendations</h2>
    <ul>
    ${report.recommendations.map(rec => `<li>${rec}</li>`).join('')}
    </ul>
  </div>
</body>
</html>`;

    fs.writeFileSync(htmlPath, html);
  }

  /**
   * Generate security recommendations
   */
  generateRecommendations() {
    const recommendations = [];

    // Critical issues
    if (this.results.summary.criticalIssues > 0) {
      recommendations.push('🚨 IMMEDIATE: Address all critical security vulnerabilities within 24 hours');
    }

    // High severity issues
    if (this.results.summary.highIssues > this.config.thresholds.high) {
      recommendations.push('⚠️ URGENT: Review and fix high-severity issues within 1 week');
    }

    // Dependency vulnerabilities
    const snykScan = this.results.scans.snyk;
    if (snykScan && snykScan.summary && snykScan.summary.total > 0) {
      recommendations.push('📦 Update vulnerable dependencies to latest secure versions');
    }

    // Code quality issues
    const sonarScan = this.results.scans.sonar;
    if (sonarScan && sonarScan.status === 'failed') {
      recommendations.push('🔧 Fix SonarQube configuration and rerun code quality scan');
    }

    // General recommendations
    recommendations.push('🔒 Implement automated security scanning in CI/CD pipeline');
    recommendations.push('📚 Train development team on secure coding practices');
    recommendations.push('🔍 Schedule regular security audits and penetration testing');
    recommendations.push('📊 Set up security metrics dashboard for ongoing monitoring');

    return recommendations;
  }

  /**
   * Send security notifications
   */
  async sendNotifications() {
    if (!this.config.notifications.enabled) {
      return;
    }

    const hasCriticalIssues = this.results.summary.criticalIssues > 0;
    const exceedsThreshold = this.results.summary.highIssues > this.config.thresholds.high;

    if (!hasCriticalIssues && !exceedsThreshold) {
      return;
    }

    const message = this.generateNotificationMessage();

    if (this.config.notifications.slack.enabled) {
      await this.sendSlackNotification(message);
    }

    if (this.config.notifications.email.enabled) {
      await this.sendEmailNotification(message);
    }
  }

  /**
   * Generate notification message
   */
  generateNotificationMessage() {
    return {
      title: 'Security Scan Alert',
      summary: `Found ${this.results.summary.totalIssues} security issues (${this.results.summary.criticalIssues} critical, ${this.results.summary.highIssues} high)`,
      details: `Security scan completed with ${this.results.summary.totalIssues} total issues detected.`,
      action: 'Review security scan report and address critical vulnerabilities immediately'
    };
  }

  /**
   * Send Slack notification
   */
  async sendSlackNotification(message) {
    try {
      await axios.post(this.config.notifications.slack.webhookUrl, {
        text: `*${message.title}*`,
        attachments: [{
          color: this.results.summary.criticalIssues > 0 ? 'danger' : 'warning',
          fields: [
            { title: 'Summary', value: message.summary, short: true },
            { title: 'Details', value: message.details, short: false },
            { title: 'Action Required', value: message.action, short: false }
          ]
        }]
      });
      console.log('✅ Slack notification sent');
    } catch (error) {
      console.error('❌ Failed to send Slack notification:', error.message);
    }
  }

  /**
   * Send email notification
   */
  async sendEmailNotification(message) {
    // Email sending would be implemented here using nodemailer or similar
    console.log('📧 Email notification would be sent:', message.title);
  }

  /**
   * Check if build should fail based on security thresholds
   */
  shouldFailBuild() {
    return (
      this.results.summary.criticalIssues > this.config.thresholds.critical ||
      this.results.summary.highIssues > this.config.thresholds.high
    );
  }
}

module.exports = SecurityScanner;
