#!/usr/bin/env node

/**
 * Documentation Maintenance Script
 * Handles automated maintenance tasks for the documentation system
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

class DocsMaintenance {
  constructor() {
    this.docsDir = path.join(__dirname, '..', 'Docs');
    this.colors = {
      red: '\x1b[31m',
      green: '\x1b[32m',
      yellow: '\x1b[33m',
      blue: '\x1b[34m',
      reset: '\x1b[0m'
    };
  }

  log(message, color = 'reset') {
    console.log(`${this.colors[color]}${message}${this.colors.reset}`);
  }

  success(message) {
    this.log(`✅ ${message}`, 'green');
  }

  warning(message) {
    this.log(`⚠️  ${message}`, 'yellow');
  }

  error(message) {
    this.log(`❌ ${message}`, 'red');
  }

  info(message) {
    this.log(`ℹ️  ${message}`, 'blue');
  }

  /**
   * Validate documentation completeness
   */
  validateCompleteness() {
    this.info('Validating documentation completeness...');

    const issues = [];

    // Check for required directories
    const requiredDirs = [
      '01_Planning_Phase',
      '02_Development_Phase',
      '03_Risk_Management',
      '04_Deployment_Operations',
      '05_References',
      '_AI_Guidance'
    ];

    requiredDirs.forEach(dir => {
      const dirPath = path.join(this.docsDir, dir);
      if (!fs.existsSync(dirPath)) {
        issues.push({
          type: 'missing_directory',
          severity: 'high',
          message: `Required directory missing: ${dir}`
        });
      }
    });

    // Check for required files
    const requiredFiles = [
      'README.md',
      '01_Planning_Phase/README.md',
      '02_Development_Phase/README.md',
      '03_Risk_Management/README.md',
      '04_Deployment_Operations/README.md',
      '05_References/README.md',
      '_AI_Guidance/README.md'
    ];

    requiredFiles.forEach(file => {
      const filePath = path.join(this.docsDir, file);
      if (!fs.existsSync(filePath)) {
        issues.push({
          type: 'missing_file',
          severity: 'high',
          message: `Required file missing: ${file}`
        });
      }
    });

    return issues;
  }

  /**
   * Check for broken links and references
   */
  checkLinks() {
    this.info('Checking for broken links and references...');

    const issues = [];
    const allFiles = this.getAllMarkdownFiles();

    allFiles.forEach(file => {
      const content = fs.readFileSync(file, 'utf8');
      const lines = content.split('\n');

      lines.forEach((line, index) => {
        // Check for markdown links
        const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
        let match;

        while ((match = linkRegex.exec(line)) !== null) {
          const linkText = match[1];
          const linkUrl = match[2];

          // Check internal markdown links
          if (linkUrl.startsWith('./') || linkUrl.startsWith('../')) {
            const linkPath = path.resolve(path.dirname(file), linkUrl);

            if (linkUrl.endsWith('.md') && !fs.existsSync(linkPath)) {
              issues.push({
                type: 'broken_link',
                severity: 'medium',
                file: path.relative(this.docsDir, file),
                line: index + 1,
                message: `Broken link: ${linkUrl}`
              });
            }
          }
        }
      });
    });

    return issues;
  }

  /**
   * Update timestamps in documentation
   */
  updateTimestamps() {
    this.info('Updating documentation timestamps...');

    const files = this.getAllMarkdownFiles();
    let updatedCount = 0;

    files.forEach(file => {
      const content = fs.readFileSync(file, 'utf8');
      const updatedContent = content.replace(
        /Last Updated:.*$/gm,
        `Last Updated: ${new Date().toISOString().split('T')[0]}`
      );

      if (content !== updatedContent) {
        fs.writeFileSync(file, updatedContent);
        this.success(`Updated timestamp in ${path.relative(this.docsDir, file)}`);
        updatedCount++;
      }
    });

    this.info(`Updated timestamps in ${updatedCount} files`);
  }

  /**
   * Check checklist completion status
   */
  checkChecklists() {
    this.info('Checking checklist completion status...');

    const issues = [];
    const files = this.getAllMarkdownFiles();

    files.forEach(file => {
      const content = fs.readFileSync(file, 'utf8');
      const totalCheckboxes = (content.match(/\[ \]/g) || []).length;
      const completedCheckboxes = (content.match(/\[x\]/g) || []).length;

      if (totalCheckboxes > 0) {
        const completionRate = (completedCheckboxes / totalCheckboxes) * 100;

        if (completionRate === 0) {
          issues.push({
            type: 'incomplete_checklist',
            severity: 'low',
            file: path.relative(this.docsDir, file),
            message: `Checklist 0% complete (${totalCheckboxes} items)`
          });
        } else if (completionRate < 50) {
          issues.push({
            type: 'incomplete_checklist',
            severity: 'medium',
            file: path.relative(this.docsDir, file),
            message: `Checklist ${completionRate.toFixed(1)}% complete (${completedCheckboxes}/${totalCheckboxes})`
          });
        }
      }
    });

    return issues;
  }

  /**
   * Generate maintenance report
   */
  generateReport(issues = []) {
    this.info('Generating maintenance report...');

    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        totalFiles: this.getAllMarkdownFiles().length,
        issuesFound: issues.length,
        criticalIssues: issues.filter(i => i.severity === 'high').length,
        warningIssues: issues.filter(i => i.severity === 'medium').length,
        infoIssues: issues.filter(i => i.severity === 'low').length
      },
      issues: issues,
      recommendations: this.generateRecommendations(issues)
    };

    const reportPath = path.join(this.docsDir, 'maintenance-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

    // Generate HTML report
    this.generateHtmlReport(report);

    this.success(`Maintenance report saved to ${reportPath}`);
    return report;
  }

  /**
   * Generate HTML report
   */
  generateHtmlReport(report) {
    const html = `
<!DOCTYPE html>
<html>
<head>
  <title>Documentation Maintenance Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    .summary { background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
    .metric { display: inline-block; margin: 10px; text-align: center; }
    .metric-value { font-size: 24px; font-weight: bold; }
    .issues { margin-top: 20px; }
    .issue { padding: 10px; margin: 5px 0; border-radius: 3px; }
    .high { background: #ffebee; border: 1px solid #f44336; }
    .medium { background: #fff3e0; border: 1px solid #ff9800; }
    .low { background: #e8f5e8; border: 1px solid #4caf50; }
    .recommendations { background: #e3f2fd; padding: 15px; border-radius: 5px; margin-top: 20px; }
  </style>
</head>
<body>
  <h1>Documentation Maintenance Report</h1>
  <p><strong>Generated:</strong> ${new Date(report.timestamp).toLocaleString()}</p>

  <div class="summary">
    <h2>Summary</h2>
    <div class="metric">
      <div class="metric-value">${report.summary.totalFiles}</div>
      <div>Total Files</div>
    </div>
    <div class="metric">
      <div class="metric-value">${report.summary.issuesFound}</div>
      <div>Issues Found</div>
    </div>
    <div class="metric">
      <div class="metric-value" style="color: #f44336;">${report.summary.criticalIssues}</div>
      <div>Critical</div>
    </div>
    <div class="metric">
      <div class="metric-value" style="color: #ff9800;">${report.summary.warningIssues}</div>
      <div>Warnings</div>
    </div>
  </div>

  <div class="issues">
    <h2>Issues Found</h2>
    ${report.issues.map(issue => `
      <div class="issue ${issue.severity}">
        <strong>${issue.type.toUpperCase()}</strong> - ${issue.file || 'General'}
        <br>${issue.message}
      </div>
    `).join('')}
  </div>

  <div class="recommendations">
    <h2>Recommendations</h2>
    <ul>
    ${report.recommendations.map(rec => `<li>${rec}</li>`).join('')}
    </ul>
  </div>
</body>
</html>`;

    const htmlPath = path.join(this.docsDir, 'maintenance-report.html');
    fs.writeFileSync(htmlPath, html);
    this.success(`HTML report saved to ${htmlPath}`);
  }

  /**
   * Generate recommendations based on issues
   */
  generateRecommendations(issues) {
    const recommendations = [];

    const criticalCount = issues.filter(i => i.severity === 'high').length;
    const linkIssues = issues.filter(i => i.type === 'broken_link').length;
    const checklistIssues = issues.filter(i => i.type === 'incomplete_checklist').length;

    if (criticalCount > 0) {
      recommendations.push('Address all critical issues immediately (missing files/directories)');
    }

    if (linkIssues > 0) {
      recommendations.push('Fix broken links to maintain documentation integrity');
    }

    if (checklistIssues > 0) {
      recommendations.push('Complete or remove outdated checklists in documentation');
    }

    if (recommendations.length === 0) {
      recommendations.push('Documentation is in good condition - continue regular maintenance');
    }

    return recommendations;
  }

  /**
   * Get all markdown files in docs directory
   */
  getAllMarkdownFiles() {
    const files = [];

    function scanDirectory(dir) {
      const items = fs.readdirSync(dir);

      items.forEach(item => {
        const fullPath = path.join(dir, item);
        const stat = fs.statSync(fullPath);

        if (stat.isDirectory()) {
          scanDirectory(fullPath);
        } else if (item.endsWith('.md')) {
          files.push(fullPath);
        }
      });
    }

    scanDirectory(this.docsDir);
    return files;
  }

  /**
   * Run all maintenance checks
   */
  async runAllChecks() {
    this.info('Starting comprehensive documentation maintenance...');

    const allIssues = [
      ...this.validateCompleteness(),
      ...this.checkLinks(),
      ...this.checkChecklists()
    ];

    this.updateTimestamps();

    const report = this.generateReport(allIssues);

    this.info(`Maintenance completed. Found ${allIssues.length} issues.`);

    return report;
  }
}

// CLI interface
async function main() {
  const maintenance = new DocsMaintenance();
  const args = process.argv.slice(2);

  if (args.includes('--post-commit')) {
    // Light maintenance for post-commit hook
    maintenance.updateTimestamps();
    maintenance.success('Post-commit maintenance completed');
  } else if (args.includes('--validate')) {
    const issues = [
      ...maintenance.validateCompleteness(),
      ...maintenance.checkLinks(),
      ...maintenance.checkChecklists()
    ];
    maintenance.generateReport(issues);
  } else {
    // Full maintenance run
    await maintenance.runAllChecks();
  }
}

if (require.main === module) {
  main().catch(error => {
    console.error('Maintenance script failed:', error);
    process.exit(1);
  });
}

module.exports = DocsMaintenance;
