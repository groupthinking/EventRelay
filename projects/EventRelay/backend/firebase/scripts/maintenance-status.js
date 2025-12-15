#!/usr/bin/env node

/**
 * Documentation Maintenance Status Script
 * Provides overview of current maintenance system status
 */

const fs = require('fs');
const path = require('path');

class MaintenanceStatus {
  constructor() {
    this.rootDir = path.join(__dirname, '..');
    this.docsDir = path.join(this.rootDir, 'Docs');
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
   * Check Git hooks status
   */
  checkGitHooks() {
    this.info('Checking Git hooks...');

    const hooksDir = path.join(this.rootDir, '.git', 'hooks');
    const requiredHooks = ['pre-commit', 'post-commit'];
    const status = { installed: [], missing: [] };

    requiredHooks.forEach(hook => {
      const hookPath = path.join(hooksDir, hook);
      if (fs.existsSync(hookPath)) {
        // Check if executable
        try {
          const stats = fs.statSync(hookPath);
          const isExecutable = !!(stats.mode & parseInt('111', 8));
          if (isExecutable) {
            status.installed.push(hook);
          } else {
            status.missing.push(`${hook} (not executable)`);
          }
        } catch (error) {
          status.missing.push(`${hook} (error checking)`);
        }
      } else {
        status.missing.push(hook);
      }
    });

    return status;
  }

  /**
   * Check maintenance scripts
   */
  checkScripts() {
    this.info('Checking maintenance scripts...');

    const scriptsDir = path.join(this.rootDir, 'scripts');
    const requiredScripts = [
      'docs-maintenance.js',
      'create-doc-templates.js',
      'maintenance-status.js'
    ];

    const status = { present: [], missing: [] };

    requiredScripts.forEach(script => {
      const scriptPath = path.join(scriptsDir, script);
      if (fs.existsSync(scriptPath)) {
        status.present.push(script);
      } else {
        status.missing.push(script);
      }
    });

    return status;
  }

  /**
   * Check package.json scripts
   */
  checkPackageScripts() {
    this.info('Checking package.json scripts...');

    const packagePath = path.join(this.rootDir, 'package.json');

    if (!fs.existsSync(packagePath)) {
      return { error: 'package.json not found' };
    }

    try {
      const packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
      const scripts = packageJson.scripts || {};

      const expectedScripts = [
        'docs:validate',
        'docs:update',
        'docs:create-templates',
        'docs:check-links',
        'docs:daily-update',
        'docs:weekly-review',
        'docs:monthly-audit'
      ];

      const status = { present: [], missing: [] };

      expectedScripts.forEach(script => {
        if (scripts[script]) {
          status.present.push(script);
        } else {
          status.missing.push(script);
        }
      });

      return status;
    } catch (error) {
      return { error: 'Error parsing package.json' };
    }
  }

  /**
   * Check GitHub Actions workflows
   */
  checkGitHubActions() {
    this.info('Checking GitHub Actions workflows...');

    const workflowsDir = path.join(this.rootDir, '.github', 'workflows');
    const expectedWorkflows = ['docs-maintenance.yml'];

    if (!fs.existsSync(workflowsDir)) {
      return { error: '.github/workflows directory not found' };
    }

    const status = { present: [], missing: [] };

    expectedWorkflows.forEach(workflow => {
      const workflowPath = path.join(workflowsDir, workflow);
      if (fs.existsSync(workflowPath)) {
        status.present.push(workflow);
      } else {
        status.missing.push(workflow);
      }
    });

    return status;
  }

  /**
   * Check documentation structure
   */
  checkDocStructure() {
    this.info('Checking documentation structure...');

    const expectedDirs = [
      '01_Planning_Phase',
      '02_Development_Phase',
      '03_Risk_Management',
      '04_Deployment_Operations',
      '05_References',
      '_AI_Guidance'
    ];

    const status = { present: [], missing: [] };

    expectedDirs.forEach(dir => {
      const dirPath = path.join(this.docsDir, dir);
      if (fs.existsSync(dirPath)) {
        status.present.push(dir);

        // Check for README
        const readmePath = path.join(dirPath, 'README.md');
        if (!fs.existsSync(readmePath)) {
          status.missing.push(`${dir}/README.md`);
        }
      } else {
        status.missing.push(dir);
      }
    });

    return status;
  }

  /**
   * Generate comprehensive status report
   */
  generateReport() {
    console.log('🚀 Documentation Maintenance System Status\n');

    // Git Hooks
    const hooksStatus = this.checkGitHooks();
    console.log('📋 Git Hooks:');
    hooksStatus.installed.forEach(hook => this.success(`${hook} installed and executable`));
    hooksStatus.missing.forEach(hook => this.error(`${hook} missing or not executable`));
    console.log('');

    // Scripts
    const scriptsStatus = this.checkScripts();
    console.log('📜 Maintenance Scripts:');
    scriptsStatus.present.forEach(script => this.success(`${script} present`));
    scriptsStatus.missing.forEach(script => this.error(`${script} missing`));
    console.log('');

    // Package Scripts
    const packageStatus = this.checkPackageScripts();
    console.log('📦 Package.json Scripts:');
    if (packageStatus.error) {
      this.error(packageStatus.error);
    } else {
      packageStatus.present.forEach(script => this.success(`${script} defined`));
      packageStatus.missing.forEach(script => this.error(`${script} missing`));
    }
    console.log('');

    // GitHub Actions
    const actionsStatus = this.checkGitHubActions();
    console.log('🔄 GitHub Actions Workflows:');
    if (actionsStatus.error) {
      this.error(actionsStatus.error);
    } else {
      actionsStatus.present.forEach(workflow => this.success(`${workflow} present`));
      actionsStatus.missing.forEach(workflow => this.error(`${workflow} missing`));
    }
    console.log('');

    // Documentation Structure
    const docsStatus = this.checkDocStructure();
    console.log('📁 Documentation Structure:');
    docsStatus.present.forEach(dir => this.success(`${dir} directory present`));
    docsStatus.missing.forEach(item => this.error(`${item} missing`));
    console.log('');

    // Overall Status
    const allGood =
      hooksStatus.missing.length === 0 &&
      scriptsStatus.missing.length === 0 &&
      (!packageStatus.error && packageStatus.missing.length === 0) &&
      (!actionsStatus.error && actionsStatus.missing.length === 0) &&
      docsStatus.missing.length === 0;

    console.log('🎯 Overall Status:');
    if (allGood) {
      this.success('All maintenance system components are properly configured!');
      this.info('Your documentation maintenance system is ready to use.');
    } else {
      this.warning('Some maintenance system components need attention.');
      this.info('Run the setup commands to complete the configuration.');
    }
    console.log('');

    // Next Steps
    console.log('📋 Next Steps:');
    if (!allGood) {
      console.log('1. Fix missing components listed above');
      console.log('2. Run: npm run docs:validate');
      console.log('3. Test with: git add . && git commit -m "test"');
    }
    console.log('4. Set up monitoring: npm run docs:daily-update');
    console.log('5. Configure alerts for weekly/monthly reviews');

    return {
      hooks: hooksStatus,
      scripts: scriptsStatus,
      package: packageStatus,
      actions: actionsStatus,
      docs: docsStatus,
      overall: allGood
    };
  }
}

// CLI interface
function main() {
  const status = new MaintenanceStatus();
  const report = status.generateReport();

  // Exit with appropriate code
  if (!report.overall) {
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = MaintenanceStatus;
