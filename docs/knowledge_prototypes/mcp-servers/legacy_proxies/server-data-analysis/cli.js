#!/usr/bin/env node

/**
 * MCP Service CLI
 * Command-line interface for MCP services
 */

import createInterface from './index.js';
import { parseArgs } from 'node:util';

// Parse command line arguments
const args = process.argv.slice(2);
console.log(`Command arguments: ${args.join(' ')}`);

// Parse options into capabilities
const options = {};
for (const arg of args) {
  if (arg.startsWith('--')) {
    const [key, value] = arg.substring(2).split('=');
    options[key] = value === undefined ? true : value;
  }
}

// Create service interface
const service = createInterface({
  options
});

// Initialize service
try {
  await service.initialize();
  console.log(`Service activated with capabilities:`, await service.getCapabilities());
  
  // Keep process alive
  console.log(`data-analysis running in bridge mode. Press Ctrl+C to terminate.`);
  setInterval(() => {}, 10000);
} catch (error) {
  console.error(`Failed to initialize service:`, error.message);
  process.exit(1);
}
