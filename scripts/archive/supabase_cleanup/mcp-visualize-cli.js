#!/usr/bin/env node

/**
 * MCP Context Visualizer CLI
 * 
 * Command-line interface for the MCP Context Visualizer
 * 
 * Usage:
 *   node mcp-visualize-cli.js [options]
 * 
 * Options:
 *   --input <file>        Input context file (JSON)
 *   --output <file>       Output visualization file (HTML)
 *   --connect             Connect to MCP Orchestrator and visualize live contexts
 *   --analyze             Generate analytics only (no visualization)
 *   --sources <sources>   Filter by sources (comma-separated)
 *   --operations <ops>    Filter by operations (comma-separated)
 *   --help                Show help
 */

const fs = require('fs');
const path = require('path');
const { MCPContextVisualizer } = require('./mcp-context-visualizer');
const { MCPOrchestrator } = require('./mcp-orchestrator');

// Parse command line arguments
const args = process.argv.slice(2);
const options = parseArgs(args);

// Show help if requested or no arguments provided
if (options.help || args.length === 0) {
  showHelp();
  process.exit(0);
}

// Main function
async function main() {
  console.log('\n=== MCP Context Visualizer CLI ===\n');
  
  // Create visualizer
  const visualizer = new MCPContextVisualizer();
  
  // Load contexts if input file specified
  if (options.input) {
    console.log(`Loading contexts from ${options.input}...`);
    if (!fs.existsSync(options.input)) {
      console.error(`Error: Input file ${options.input} not found`);
      process.exit(1);
    }
    
    visualizer.loadFromFile(options.input);
  }
  
  // Connect to orchestrator if requested
  if (options.connect) {
    console.log('Connecting to MCP Orchestrator...');
    const orchestrator = new MCPOrchestrator({ visualize: false });
    
    // Run demo extraction to generate some contexts
    console.log('Extracting sample contexts from orchestrator...');
    await runDemoExtraction(orchestrator);
    
    // Import contexts from orchestrator
    visualizer.importFromOrchestrator(orchestrator);
  }
  
  // Apply filters if specified
  let contexts = visualizer.getContexts();
  console.log(`Loaded ${contexts.length} contexts`);
  
  if (options.sources) {
    const sources = options.sources.split(',');
    contexts = contexts.filter(ctx => 
      ctx.parameters && sources.includes(ctx.parameters.source)
    );
    console.log(`Filtered to ${contexts.length} contexts by sources: ${sources.join(', ')}`);
  }
  
  if (options.operations) {
    const operations = options.operations.split(',');
    contexts = contexts.filter(ctx => 
      operations.includes(ctx.operation)
    );
    console.log(`Filtered to ${contexts.length} contexts by operations: ${operations.join(', ')}`);
  }
  
  // Make sure we have contexts to visualize
  if (contexts.length === 0) {
    console.error('Error: No contexts to visualize after filtering');
    process.exit(1);
  }
  
  // Generate analytics
  console.log('\nGenerating analytics...');
  const analytics = visualizer.analyzeContexts();
  console.log(JSON.stringify(analytics, null, 2));
  
  // Generate visualization if not analyze-only
  if (!options.analyze) {
    const outputFile = options.output || 'mcp-visualization.html';
    console.log(`\nGenerating visualization to ${outputFile}...`);
    visualizer.generateHtmlVisualization(outputFile);
    console.log(`Visualization saved to ${outputFile}`);
    console.log(`Open file://${path.resolve(outputFile)} in your browser to view`);
  }
  
  console.log('\nDone!');
}

/**
 * Parse command line arguments
 */
function parseArgs(args) {
  const options = {};
  
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    
    if (arg === '--help') {
      options.help = true;
    } else if (arg === '--input' && i + 1 < args.length) {
      options.input = args[++i];
    } else if (arg === '--output' && i + 1 < args.length) {
      options.output = args[++i];
    } else if (arg === '--connect') {
      options.connect = true;
    } else if (arg === '--analyze') {
      options.analyze = true;
    } else if (arg === '--sources' && i + 1 < args.length) {
      options.sources = args[++i];
    } else if (arg === '--operations' && i + 1 < args.length) {
      options.operations = args[++i];
    }
  }
  
  return options;
}

/**
 * Show help message
 */
function showHelp() {
  console.log(`
MCP Context Visualizer CLI

Visualize and analyze MCP contexts from the command line.

Usage:
  node mcp-visualize-cli.js [options]

Options:
  --input <file>        Input context file (JSON)
  --output <file>       Output visualization file (HTML)
  --connect             Connect to MCP Orchestrator and visualize live contexts
  --analyze             Generate analytics only (no visualization)
  --sources <sources>   Filter by sources (comma-separated)
  --operations <ops>    Filter by operations (comma-separated)
  --help                Show this help message

Examples:
  # Load contexts from file and generate visualization
  node mcp-visualize-cli.js --input contexts.json --output viz.html

  # Connect to orchestrator and visualize live contexts
  node mcp-visualize-cli.js --connect

  # Generate analytics only for specific sources
  node mcp-visualize-cli.js --input contexts.json --analyze --sources claude,github
  `);
}

/**
 * Run a demo extraction with the orchestrator
 */
async function runDemoExtraction(orchestrator) {
  try {
    // Extract from Claude
    await orchestrator.extract('claude', { 
      conversationId: 'conv_cli_demo_' + Date.now().toString(36)
    });
    
    // Extract from GitHub
    await orchestrator.extract('github', {
      repoPath: 'mcp-framework/cli-demo',
      branch: 'main',
      path: ''
    });
    
    // Extract from multiple sources in parallel
    await orchestrator.extractMultiple([
      {
        source: 'claude',
        parameters: { conversationId: 'conv_cli_multi_' + Date.now().toString(36) }
      },
      {
        source: 'github',
        parameters: { repoPath: 'mcp-framework/another-repo' }
      }
    ]);
    
    console.log('Sample context extraction complete');
  } catch (error) {
    console.error('Error during sample extraction:', error.message);
  }
}

// Run main function
main().catch(error => {
  console.error('Error:', error);
  process.exit(1);
}); 