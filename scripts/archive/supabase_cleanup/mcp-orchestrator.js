/**
 * MCP Orchestrator
 * 
 * This module provides a central orchestration point for all MCP extractors,
 * making it easy to extract data from multiple sources and combine the results.
 */

// Using modern import syntax for node-fetch
const { default: fetch } = require('node-fetch');

// Import individual extractors (these would be in separate files in a real project)
const claudeExtractor = require('./claude-mcp-extractor');
const githubExtractor = require('./github-mcp-extractor');

// Import the Context Visualizer (optional, loaded dynamically if available)
let MCPContextVisualizer;
try {
  MCPContextVisualizer = require('./mcp-context-visualizer').MCPContextVisualizer;
} catch (e) {
  // Visualizer not available, will use null instead
  MCPContextVisualizer = null;
}

// Supabase MCP endpoint configuration
const MCP_CONFIG = {
  endpoint: 'https://nsfrhirwsjqwhagtuaxx.supabase.co/functions/v1/connect-to-cursor-mcp',
  anonKey: 'REDACTED_JWT_ROTATE'
};

/**
 * MCP Orchestrator Class
 */
class MCPOrchestrator {
  constructor(config = {}) {
    this.config = { ...MCP_CONFIG, ...config };
    this.extractors = new Map();
    this.contextTracker = new Map();
    
    // Initialize visualizer if available and enabled
    this.visualizer = null;
    if (config.visualize !== false && MCPContextVisualizer) {
      this.visualizer = new MCPContextVisualizer(config.visualizerConfig || {});
      console.log('MCP Context Visualizer initialized');
    }
    
    // Register built-in extractors (in a real app, these would be dynamically loaded)
    this.registerExtractor('claude', claudeExtractor.extractFromClaude);
    this.registerExtractor('github', githubExtractor.extractFromGitHub);
    
    // Note: In a production environment, you would load these dynamically
    // or initialize them with proper configuration
  }
  
  /**
   * Register a new extractor
   */
  registerExtractor(source, extractorFn) {
    if (typeof extractorFn !== 'function') {
      throw new Error(`Extractor for ${source} must be a function`);
    }
    
    this.extractors.set(source, extractorFn);
    console.log(`Registered extractor for source: ${source}`);
    return this;
  }
  
  /**
   * Extract data from a specific source
   */
  async extract(source, parameters = {}) {
    console.log(`Orchestrating extraction from ${source} with parameters:`, parameters);
    
    const extractorFn = this.extractors.get(source);
    if (!extractorFn) {
      throw new Error(`No extractor registered for source: ${source}`);
    }
    
    try {
      // Call the source-specific extractor
      const result = await extractorFn(...Object.values(parameters));
      
      // Extract the context_id from the response
      // The Supabase edge function returns { message, context } structure
      const contextData = result.context || result;
      const contextId = contextData.context_id;
      
      if (contextId) {
        // Track the context for potential combining later
        this.contextTracker.set(contextId, {
          source,
          parameters,
          timestamp: Date.now(),
          result: contextData
        });
        
        // Add to visualizer if available
        if (this.visualizer) {
          this.visualizer.addContext(contextData);
        }
        
        console.log(`Tracked context with ID: ${contextId}`);
      } else {
        console.warn(`No context_id found in result from ${source}`);
      }
      
      return {
        context_id: contextId,
        ...result
      };
    } catch (error) {
      console.error(`Error extracting from ${source}:`, error);
      throw error;
    }
  }
  
  /**
   * Extract data from multiple sources in parallel
   */
  async extractMultiple(extractionRequests) {
    console.log(`Orchestrating multiple extractions:`, 
      extractionRequests.map(req => req.source).join(', '));
    
    const promises = extractionRequests.map(request => 
      this.extract(request.source, request.parameters)
    );
    
    return Promise.all(promises);
  }
  
  /**
   * Combine multiple contexts into a single MCP context
   */
  async combineContexts(contextIds, name = 'combined-extraction') {
    console.log(`Combining contexts: ${contextIds.join(', ')}`);
    
    // Filter out any undefined or null context IDs
    contextIds = contextIds.filter(id => id);
    
    if (contextIds.length === 0) {
      throw new Error('No valid context IDs provided for combining');
    }
    
    // Gather contexts to combine
    const contextsToInclude = {};
    const sourcesIncluded = [];
    
    for (const contextId of contextIds) {
      const trackedContext = this.contextTracker.get(contextId);
      if (!trackedContext) {
        console.warn(`Context ID not found in tracker: ${contextId}`);
        continue;
      }
      
      contextsToInclude[trackedContext.source] = trackedContext.result;
      sourcesIncluded.push(trackedContext.source);
    }
    
    if (Object.keys(contextsToInclude).length === 0) {
      throw new Error('No valid contexts found for combining');
    }
    
    // Create combined MCP context
    const combinedContext = {
      context_id: `${name}-${Date.now()}`,
      operation: "combine",
      parameters: {
        sources: sourcesIncluded,
        contextIds
      },
      result: contextsToInclude,
      metadata: {
        combinationTime: new Date().toISOString(),
        sourceCount: sourcesIncluded.length
      }
    };
    
    console.log(`Created combined context with ID: ${combinedContext.context_id}`);
    
    // Add to visualizer if available
    if (this.visualizer) {
      this.visualizer.addContext(combinedContext);
    }
    
    // Send to MCP endpoint
    return this.sendToMcpEndpoint(combinedContext);
  }
  
  /**
   * Send context to MCP endpoint
   */
  async sendToMcpEndpoint(mcpContext, modelId = 'mcp-orchestrator') {
    console.log(`Sending to MCP endpoint: ${this.config.endpoint}`);
    
    const requestBody = {
      modelId,
      context: mcpContext
    };
    
    try {
      const response = await fetch(this.config.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.anonKey}`
        },
        body: JSON.stringify(requestBody)
      });
      
      if (!response.ok) {
        throw new Error(`MCP endpoint error: ${response.status}`);
      }
      
      const result = await response.json();
      return result;
    } catch (error) {
      console.error("Error sending to MCP endpoint:", error.message);
      throw error;
    }
  }
  
  /**
   * Get list of registered extractors
   */
  getRegisteredExtractors() {
    return Array.from(this.extractors.keys());
  }
  
  /**
   * Get tracked contexts
   */
  getTrackedContexts() {
    return Array.from(this.contextTracker.entries()).map(([id, data]) => ({
      context_id: id,
      source: data.source,
      timestamp: data.timestamp
    }));
  }
  
  /**
   * Generate visualization of current contexts (if visualizer is available)
   */
  generateVisualization(outputPath) {
    if (!this.visualizer) {
      console.warn('Context Visualizer is not available');
      return null;
    }
    
    return this.visualizer.generateHtmlVisualization(outputPath);
  }
  
  /**
   * Analyze current contexts (if visualizer is available)
   */
  analyzeContexts() {
    if (!this.visualizer) {
      console.warn('Context Visualizer is not available');
      return null;
    }
    
    return this.visualizer.analyzeContexts();
  }
  
  /**
   * Export contexts to file (if visualizer is available)
   */
  exportContextsToFile(filePath) {
    if (!this.visualizer) {
      console.warn('Context Visualizer is not available');
      return false;
    }
    
    return this.visualizer.saveToFile(filePath);
  }
  
  /**
   * Import contexts from file (if visualizer is available)
   */
  importContextsFromFile(filePath) {
    if (!this.visualizer) {
      console.warn('Context Visualizer is not available');
      return false;
    }
    
    return this.visualizer.loadFromFile(filePath);
  }
}

/**
 * Example usage of the MCP Orchestrator
 */
async function demoOrchestrator() {
  // Create orchestrator instance with visualization enabled
  const orchestrator = new MCPOrchestrator({ visualize: true });
  
  try {
    console.log("=== MCP Orchestrator Demo ===");
    console.log("Registered extractors:", orchestrator.getRegisteredExtractors());
    
    // Extract from Claude
    console.log("\n--- Claude Extraction ---");
    const claudeResult = await orchestrator.extract('claude', { 
      conversationId: 'conv_demo_' + Date.now().toString(36)
    });
    console.log("Claude extraction complete with context ID:", claudeResult.context_id);
    
    // Extract from GitHub
    console.log("\n--- GitHub Extraction ---");
    const githubResult = await orchestrator.extract('github', {
      repoPath: 'mcp-framework/github-extractor',
      branch: 'main',
      path: ''
    });
    console.log("GitHub extraction complete with context ID:", githubResult.context_id);
    
    // Extract from multiple sources in parallel
    console.log("\n--- Parallel Extraction ---");
    const multiResults = await orchestrator.extractMultiple([
      {
        source: 'claude',
        parameters: { conversationId: 'conv_multi_' + Date.now().toString(36) }
      },
      {
        source: 'github',
        parameters: { repoPath: 'mcp-framework/another-repo' }
      }
    ]);
    
    const contextIds = multiResults.map(r => r.context_id).filter(id => id);
    console.log("Parallel extraction complete with context IDs:", contextIds.join(', '));
    
    // Combine contexts from the first two extractions
    if (claudeResult.context_id && githubResult.context_id) {
      console.log("\n--- Context Combination ---");
      const combinedResult = await orchestrator.combineContexts(
        [claudeResult.context_id, githubResult.context_id],
        'demo-combination'
      );
      console.log("Context combination complete:", combinedResult);
    }
    
    // Generate visualization if available
    if (orchestrator.visualizer) {
      console.log("\n--- Context Visualization ---");
      const path = require('path');
      const outputPath = path.join(__dirname, 'mcp-orchestrator-demo.html');
      orchestrator.generateVisualization(outputPath);
      console.log(`Visualization generated at: ${outputPath}`);
      
      // Analyze contexts
      console.log("\n--- Context Analytics ---");
      const analytics = orchestrator.analyzeContexts();
      console.log("Context analytics:", JSON.stringify(analytics, null, 2));
    }
    
    console.log("\nDemo completed successfully!");
    console.log("Tracked contexts:", orchestrator.getTrackedContexts());
  } catch (error) {
    console.error("Demo failed:", error);
  }
}

// If this module is run directly, run the demo
if (require.main === module) {
  demoOrchestrator().catch(console.error);
}

// Export for use in other modules
module.exports = {
  MCPOrchestrator,
  demoOrchestrator
}; 