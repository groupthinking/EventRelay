/**
 * MCP Context Visualizer
 * 
 * This module provides visualization tools for MCP contexts, allowing developers
 * to understand and analyze context flow through the system.
 */

const { default: fetch } = require('node-fetch');
const fs = require('fs');
const path = require('path');

// Supabase MCP endpoint configuration
const MCP_CONFIG = {
  endpoint: 'https://nsfrhirwsjqwhagtuaxx.supabase.co/functions/v1/connect-to-cursor-mcp',
  anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5zZnJoaXJ3c2pxd2hhZ3R1YXh4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDYyMTcwMTMsImV4cCI6MjA2MTc5MzAxM30.mvPT1ha9keOLFCxVPoUoAwWt2uKb-m_ii2bu2I-ziyk'
};

/**
 * MCP Context Visualizer Class
 */
class MCPContextVisualizer {
  constructor(config = {}) {
    this.config = { ...MCP_CONFIG, ...config };
    this.contexts = new Map();
    this.contextRelationships = new Map();
  }

  /**
   * Register an MCP context with the visualizer
   */
  addContext(context) {
    if (!context.context_id) {
      throw new Error('Context must have a context_id property');
    }

    // Store the context
    this.contexts.set(context.context_id, {
      ...context,
      addedAt: Date.now()
    });

    // If this context has relationships to other contexts, record them
    if (context.parameters && context.parameters.contextIds) {
      const parentIds = Array.isArray(context.parameters.contextIds) 
        ? context.parameters.contextIds 
        : [context.parameters.contextIds];
      
      for (const parentId of parentIds) {
        if (!this.contextRelationships.has(parentId)) {
          this.contextRelationships.set(parentId, new Set());
        }
        this.contextRelationships.get(parentId).add(context.context_id);
      }
    }

    return this;
  }

  /**
   * Import contexts from the MCP orchestrator
   */
  importFromOrchestrator(orchestrator) {
    const contexts = orchestrator.getTrackedContexts();
    
    for (const { context_id } of contexts) {
      const contextData = orchestrator.contextTracker.get(context_id);
      if (contextData && contextData.result) {
        this.addContext(contextData.result);
      }
    }
    
    console.log(`Imported ${contexts.length} contexts from orchestrator`);
    return this;
  }

  /**
   * Load contexts from a JSON file
   */
  loadFromFile(filePath) {
    try {
      const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      
      if (Array.isArray(data)) {
        for (const context of data) {
          this.addContext(context);
        }
        console.log(`Loaded ${data.length} contexts from ${filePath}`);
      } else if (data.context_id) {
        this.addContext(data);
        console.log(`Loaded 1 context from ${filePath}`);
      } else {
        console.warn(`Invalid context data in ${filePath}`);
      }
    } catch (error) {
      console.error(`Error loading contexts from ${filePath}:`, error);
    }
    
    return this;
  }

  /**
   * Save current contexts to a JSON file
   */
  saveToFile(filePath) {
    try {
      const contexts = Array.from(this.contexts.values());
      fs.writeFileSync(filePath, JSON.stringify(contexts, null, 2));
      console.log(`Saved ${contexts.length} contexts to ${filePath}`);
    } catch (error) {
      console.error(`Error saving contexts to ${filePath}:`, error);
    }
    
    return this;
  }

  /**
   * Generate a graph representation of context relationships
   */
  generateContextGraph() {
    const nodes = [];
    const edges = [];
    
    // Create nodes for each context
    for (const [contextId, context] of this.contexts.entries()) {
      nodes.push({
        id: contextId,
        label: contextId.split('-')[0], // Use first part of ID as label
        title: `${context.operation || 'unknown'} - ${contextId}`,
        group: context.parameters?.source || 'unknown'
      });
    }
    
    // Create edges between contexts
    for (const [parentId, childIds] of this.contextRelationships.entries()) {
      for (const childId of childIds) {
        edges.push({
          from: parentId,
          to: childId,
          arrows: 'to'
        });
      }
    }
    
    return { nodes, edges };
  }
  
  /**
   * Generate HTML visualization of context data
   */
  generateHtmlVisualization(outputPath) {
    const graph = this.generateContextGraph();
    const contexts = Array.from(this.contexts.values());
    
    // Create HTML content with vis.js for visualization
    const html = `
<!DOCTYPE html>
<html>
<head>
  <title>MCP Context Visualization</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <script src="https://unpkg.com/vis-data/standalone/umd/vis-data.min.js"></script>
  <style>
    body, html { margin: 0; padding: 0; font-family: Arial, sans-serif; }
    #container { width: 100%; height: 100vh; display: flex; }
    #graph { width: 70%; height: 100%; }
    #details { width: 30%; height: 100%; overflow: auto; padding: 10px; box-sizing: border-box; }
    .context-card { 
      border: 1px solid #ddd; 
      border-radius: 4px; 
      margin-bottom: 10px; 
      padding: 10px; 
    }
    .context-header { 
      font-weight: bold; 
      margin-bottom: 5px; 
      cursor: pointer;
      display: flex;
      justify-content: space-between;
    }
    .context-body { 
      display: none; 
      margin-top: 5px; 
      background: #f9f9f9;
      padding: 5px;
      border-radius: 4px;
      white-space: pre-wrap;
    }
    .expanded .context-body { display: block; }
  </style>
</head>
<body>
  <div id="container">
    <div id="graph"></div>
    <div id="details">
      <h2>MCP Context Visualization</h2>
      <p>Total Contexts: ${contexts.length}</p>
      <div id="context-list">
        ${contexts.map((ctx, i) => `
          <div class="context-card" data-id="${ctx.context_id}">
            <div class="context-header">
              <span>${ctx.operation || 'unknown'} - ${ctx.parameters?.source || 'unknown'}</span>
              <span>${new Date(ctx.addedAt).toLocaleTimeString()}</span>
            </div>
            <div class="context-body">
              <pre>${JSON.stringify(ctx, null, 2)}</pre>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  </div>
  
  <script>
    // Graph visualization
    const container = document.getElementById('graph');
    
    // Create data for vis.js
    const nodes = new vis.DataSet(${JSON.stringify(graph.nodes)});
    const edges = new vis.DataSet(${JSON.stringify(graph.edges)});
    
    // Create network
    const data = { nodes, edges };
    const options = {
      nodes: {
        shape: 'dot',
        size: 16,
        font: {
          size: 12
        }
      },
      edges: {
        width: 1,
        smooth: {
          type: 'continuous'
        }
      },
      physics: {
        stabilization: false,
        barnesHut: {
          gravitationalConstant: -80000,
          springConstant: 0.001,
          springLength: 200
        }
      },
      groups: {
        claude: { color: { background: '#9370DB' } },
        github: { color: { background: '#6E7781' } },
        cursor: { color: { background: '#0969DA' } },
        replit: { color: { background: '#F26207' } },
        gemini: { color: { background: '#1F8FFF' } },
        unknown: { color: { background: '#cccccc' } }
      }
    };
    
    // Initialize network
    const network = new vis.Network(container, data, options);
    
    // Handle node selection
    network.on('click', function(params) {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const card = document.querySelector(\`.context-card[data-id="\${nodeId}"]\`);
        if (card) {
          // Scroll to and highlight the card
          card.scrollIntoView({ behavior: 'smooth' });
          card.classList.add('expanded');
          
          // Briefly highlight with animation
          card.style.transition = 'background-color 0.5s';
          card.style.backgroundColor = '#ffffdd';
          setTimeout(() => {
            card.style.backgroundColor = '';
          }, 1000);
        }
      }
    });
    
    // Context card expansion
    document.querySelectorAll('.context-header').forEach(header => {
      header.addEventListener('click', () => {
        const card = header.parentElement;
        card.classList.toggle('expanded');
      });
    });
  </script>
</body>
</html>`;
    
    fs.writeFileSync(outputPath, html);
    console.log(`Generated visualization at ${outputPath}`);
    
    return this;
  }

  /**
   * Analyze context data for insights
   */
  analyzeContexts() {
    const contexts = Array.from(this.contexts.values());
    
    // Basic analytics
    const sources = {};
    const operations = {};
    const timeRange = { min: Infinity, max: 0 };
    
    for (const ctx of contexts) {
      // Count by source
      const source = ctx.parameters?.source || 'unknown';
      sources[source] = (sources[source] || 0) + 1;
      
      // Count by operation
      const operation = ctx.operation || 'unknown';
      operations[operation] = (operations[operation] || 0) + 1;
      
      // Track time range
      if (ctx.addedAt < timeRange.min) timeRange.min = ctx.addedAt;
      if (ctx.addedAt > timeRange.max) timeRange.max = ctx.addedAt;
    }
    
    // Context connections analysis
    const connectionCounts = {};
    for (const [parentId, childIds] of this.contextRelationships.entries()) {
      connectionCounts[parentId] = childIds.size;
    }
    
    // Sort to find most connected contexts
    const mostConnected = Object.entries(connectionCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    
    return {
      totalContexts: contexts.length,
      sourceBreakdown: sources,
      operationBreakdown: operations,
      timeRange: {
        start: new Date(timeRange.min).toISOString(),
        end: new Date(timeRange.max).toISOString(),
        durationMs: timeRange.max - timeRange.min
      },
      mostConnectedContexts: mostConnected,
      contextRelationships: this.contextRelationships.size,
      orphanedContexts: contexts.filter(ctx => 
        !Array.from(this.contextRelationships.values())
          .some(children => children.has(ctx.context_id))
      ).length
    };
  }

  /**
   * Get all contexts
   */
  getContexts() {
    return Array.from(this.contexts.values());
  }

  /**
   * Find contexts by source
   */
  findContextsBySource(source) {
    return this.getContexts().filter(
      ctx => ctx.parameters?.source === source
    );
  }

  /**
   * Find contexts by operation
   */
  findContextsByOperation(operation) {
    return this.getContexts().filter(
      ctx => ctx.operation === operation
    );
  }

  /**
   * Clear all stored contexts
   */
  clearContexts() {
    this.contexts.clear();
    this.contextRelationships.clear();
    return this;
  }
}

/**
 * Example usage of the Context Visualizer
 */
async function demoVisualizer() {
  // Import the orchestrator
  const { MCPOrchestrator } = require('./mcp-orchestrator');
  
  // Create and run the orchestrator first to generate some contexts
  console.log("Running MCP Orchestrator to generate sample contexts...");
  const orchestrator = new MCPOrchestrator();
  
  // Extract from multiple sources
  await orchestrator.extractMultiple([
    {
      source: 'claude',
      parameters: { conversationId: 'conv_vis_demo_' + Date.now().toString(36) }
    },
    {
      source: 'github',
      parameters: { repoPath: 'mcp-framework/visualizer-demo' }
    }
  ]);
  
  // Create the visualizer and import from orchestrator
  console.log("\nInitializing MCP Context Visualizer...");
  const visualizer = new MCPContextVisualizer();
  visualizer.importFromOrchestrator(orchestrator);
  
  // Generate and display analytics
  console.log("\nContext Analytics:");
  const analytics = visualizer.analyzeContexts();
  console.log(JSON.stringify(analytics, null, 2));
  
  // Generate visualization
  const outputPath = path.join(__dirname, 'mcp-visualization.html');
  visualizer.generateHtmlVisualization(outputPath);
  console.log(`\nVisualization saved to: ${outputPath}`);
  console.log("Open this file in a browser to see the context visualization");
  
  return visualizer;
}

// Run demo if this module is executed directly
if (require.main === module) {
  demoVisualizer().catch(console.error);
}

// Export the visualizer for use in other modules
module.exports = {
  MCPContextVisualizer,
  demoVisualizer
}; 