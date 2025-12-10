#!/usr/bin/env node

/**
 * MCP NPM Bridge Setup
 * Configures npm to use MCP launchers for MCP packages
 */

import fs from 'fs/promises';
import path from 'path';
import os from 'os';
import { execSync } from 'child_process';

// Configuration
const MCP_ROOT = process.env.MCP_ROOT || '/Users/garvey/Desktop/mcp-bridge';
const MCP_LAUNCHERS = path.join(MCP_ROOT, 'launchers');
const NPMRC_PATH = path.join(os.homedir(), '.npmrc');

async function setupNpmBridge() {
  console.log('🔄 Setting up npm bridge...');
  
  // Create .npmrc configuration
  try {
    // Read existing .npmrc if it exists
    let npmrc = '';
    try {
      npmrc = await fs.readFile(NPMRC_PATH, 'utf8');
    } catch (err) {
      // File doesn't exist, start with empty string
    }
    
    // Remove any existing MCP configuration
    npmrc = npmrc
      .split('\n')
      .filter(line => !line.includes('@modelcontextprotocol'))
      .join('\n');
    
    // Add MCP configuration
    npmrc += `\n\n# MCP Bridge Configuration (added ${new Date().toISOString()})\n`;
    npmrc += `@modelcontextprotocol:bin-links=false\n`;
    npmrc += `@modelcontextprotocol:scripts-prepend-node-path=false\n`;
    
    // Write updated .npmrc
    await fs.writeFile(NPMRC_PATH, npmrc);
    
    console.log(`✅ Updated npm configuration at ${NPMRC_PATH}`);
  } catch (err) {
    console.error('❌ Failed to update .npmrc:', err.message);
    return false;
  }
  
  // Create global links for MCP packages
  try {
    // Get list of launchers
    const launchers = await fs.readdir(MCP_LAUNCHERS);
    
    for (const launcher of launchers) {
      const launcherPath = path.join(MCP_LAUNCHERS, launcher);
      
      // Create global symlink
      try {
        execSync(`npm link ${launcherPath}`, { stdio: 'inherit' });
        console.log(`✅ Created global link for ${launcher}`);
      } catch (err) {
        console.error(`❌ Failed to create global link for ${launcher}:`, err.message);
      }
    }
    
    console.log('✅ All global links created');
  } catch (err) {
    console.error('❌ Failed to create global links:', err.message);
    return false;
  }
  
  console.log('✅ npm bridge setup complete');
  return true;
}

// Run setup
setupNpmBridge().then(success => {
  if (!success) {
    process.exit(1);
  }
});
