#!/usr/bin/env node

/**
 * PLAYWRIGHT CLI AUTOMATION AGENT
 * Designed for Claude-to-Claude collaboration across different environments
 * 
 * Usage: node playwright-cli-agent.js <command> [options]
 */

const { chromium, firefox, webkit } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

// Configuration
const CONFIG = {
  outputDir: '/home/claude/playwright-output',
  logFile: '/home/claude/playwright-output/agent.log',
  stateFile: '/home/claude/playwright-output/state.json',
  screenshotDir: '/home/claude/playwright-output/screenshots',
};

// Logging utility
async function log(message, level = 'INFO') {
  const timestamp = new Date().toISOString();
  const logEntry = `[${timestamp}] [${level}] ${message}\n`;
  
  console.log(logEntry.trim());
  
  try {
    await fs.mkdir(path.dirname(CONFIG.logFile), { recursive: true });
    await fs.appendFile(CONFIG.logFile, logEntry);
  } catch (err) {
    console.error('Logging error:', err.message);
  }
}

// State management for cross-agent coordination
async function saveState(state) {
  await fs.mkdir(path.dirname(CONFIG.stateFile), { recursive: true });
  await fs.writeFile(CONFIG.stateFile, JSON.stringify(state, null, 2));
  await log(`State saved: ${JSON.stringify(state)}`);
}

async function loadState() {
  try {
    const data = await fs.readFile(CONFIG.stateFile, 'utf8');
    return JSON.parse(data);
  } catch (err) {
    return { lastCommand: null, timestamp: null, results: [] };
  }
}

// Command handlers
const commands = {
  
  // Test browser automation
  async test(args) {
    await log('Starting browser automation test...');
    
    const browser = await chromium.launch({ 
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const context = await browser.newContext();
    const page = await context.newPage();
    
    try {
      await log('Navigating to example.com...');
      await page.goto('https://example.com', { waitUntil: 'networkidle' });
      
      const title = await page.title();
      await log(`Page title: ${title}`);
      
      // Take screenshot
      await fs.mkdir(CONFIG.screenshotDir, { recursive: true });
      const screenshotPath = path.join(CONFIG.screenshotDir, `test-${Date.now()}.png`);
      await page.screenshot({ path: screenshotPath });
      await log(`Screenshot saved: ${screenshotPath}`);
      
      const result = {
        success: true,
        title,
        screenshot: screenshotPath,
        timestamp: new Date().toISOString()
      };
      
      await saveState({ lastCommand: 'test', results: [result] });
      
      return result;
      
    } finally {
      await browser.close();
      await log('Browser closed');
    }
  },

  // Navigate to URL and extract data
  async navigate(args) {
    const url = args.url || args._[1];
    if (!url) throw new Error('URL required: --url <url>');
    
    await log(`Navigating to: ${url}`);
    
    const browser = await chromium.launch({ 
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const context = await browser.newContext();
    const page = await context.newPage();
    
    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
      
      const data = await page.evaluate(() => ({
        title: document.title,
        url: window.location.href,
        headings: Array.from(document.querySelectorAll('h1, h2, h3')).map(h => ({
          tag: h.tagName,
          text: h.textContent.trim()
        })),
        links: Array.from(document.querySelectorAll('a')).slice(0, 10).map(a => ({
          text: a.textContent.trim(),
          href: a.href
        })),
        meta: {
          description: document.querySelector('meta[name="description"]')?.content,
          keywords: document.querySelector('meta[name="keywords"]')?.content,
        }
      }));
      
      // Screenshot
      await fs.mkdir(CONFIG.screenshotDir, { recursive: true });
      const screenshotPath = path.join(CONFIG.screenshotDir, `navigate-${Date.now()}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: true });
      
      const result = {
        success: true,
        url,
        data,
        screenshot: screenshotPath,
        timestamp: new Date().toISOString()
      };
      
      await saveState({ lastCommand: 'navigate', url, results: [result] });
      await log(`Navigation complete: ${JSON.stringify(data, null, 2)}`);
      
      return result;
      
    } finally {
      await browser.close();
    }
  },

  // Check health/status
  async health(args) {
    await log('Health check initiated');
    
    const state = await loadState();
    const health = {
      status: 'healthy',
      playwright_version: require('playwright/package.json').version,
      browsers: ['chromium', 'firefox', 'webkit'],
      output_dir: CONFIG.outputDir,
      last_command: state.lastCommand,
      last_run: state.timestamp,
      timestamp: new Date().toISOString()
    };
    
    await log(`Health check: ${JSON.stringify(health)}`);
    return health;
  },

  // Get current state (for cross-agent coordination)
  async status(args) {
    const state = await loadState();
    await log('Status check');
    return state;
  },

  // List available commands
  async help(args) {
    const help = {
      commands: {
        test: 'Run basic browser automation test',
        navigate: 'Navigate to URL and extract data (--url <url>)',
        health: 'Check system health and configuration',
        status: 'Get current agent state',
        help: 'Show this help message'
      },
      examples: [
        'node playwright-cli-agent.js test',
        'node playwright-cli-agent.js navigate --url https://example.com',
        'node playwright-cli-agent.js health',
        'node playwright-cli-agent.js status'
      ]
    };
    
    console.log('\n=== PLAYWRIGHT CLI AGENT ===\n');
    console.log('Available Commands:');
    Object.entries(help.commands).forEach(([cmd, desc]) => {
      console.log(`  ${cmd.padEnd(15)} ${desc}`);
    });
    console.log('\nExamples:');
    help.examples.forEach(ex => console.log(`  ${ex}`));
    console.log('\n');
    
    return help;
  }
};

// Main execution
async function main() {
  const args = process.argv.slice(2);
  const command = args[0] || 'help';
  
  // Parse arguments
  const parsedArgs = { _: args };
  for (let i = 1; i < args.length; i++) {
    if (args[i].startsWith('--')) {
      const key = args[i].slice(2);
      const value = args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true;
      parsedArgs[key] = value;
      if (value !== true) i++;
    }
  }
  
  try {
    if (!commands[command]) {
      console.error(`Unknown command: ${command}`);
      console.error('Run "node playwright-cli-agent.js help" for usage');
      process.exit(1);
    }
    
    const result = await commands[command](parsedArgs);
    
    // Output result as JSON for easy parsing by other agents
    if (command !== 'help') {
      console.log('\n=== RESULT ===');
      console.log(JSON.stringify(result, null, 2));
    }
    
  } catch (error) {
    await log(`ERROR: ${error.message}`, 'ERROR');
    console.error('\n=== ERROR ===');
    console.error(error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main().catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
}

module.exports = { commands, log, saveState, loadState };
