/**
 * Claude MCP Extractor
 * 
 * This script extracts conversation data from Claude and sends it to the MCP endpoint.
 * Currently using mock data due to API access issues.
 */

const { default: fetch } = require('node-fetch');
const config = require('./lib/config'); // Import central config
const Anthropic = require('@anthropic-ai/sdk'); // Use official SDK
const crypto = require('crypto');

// Supabase MCP endpoint
const MCP_ENDPOINT = config.SUPABASE.FUNCTION_URL;
const SUPABASE_ANON_KEY = config.SUPABASE.ANON_KEY;

// Anthropic API key
const ANTHROPIC_API_KEY = config.API_KEYS.CLAUDE;

/**
 * Anthropic API client
 */
class AnthropicAPI {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.useMock = !this.apiKey; // Use mock ONLY if no API key
    
    if (!this.useMock) {
      this.anthropic = new Anthropic({ apiKey: this.apiKey });
      console.log('Anthropic API client initialized with REAL key.');
    } else {
      console.log('Anthropic API client initialized in MOCK mode (no key found).');
    }
  }
  
  /**
   * Get conversation data - NOTE: Anthropic SDK doesn't have a direct conversation list API.
   * We'll simulate getting the last few messages or use a specific message stream.
   * For a real implementation, message history needs to be managed externally.
   */
  async getConversation(conversationId) {
    if (this.useMock) {
      console.log('Using mock data for Claude conversation');
      return this._getMockConversation(conversationId);
    }
    
    try {
      console.log(`Attempting to get messages for simulated conversation: ${conversationId}`);
      // This is a placeholder. The current SDK primarily uses `messages.create` for streaming or single requests.
      // Listing historical messages requires external storage or a different API approach.
      // Simulating a successful call with a few messages for demo.
      const mockRealMessages = [
        {
          id: `msg_live_${conversationId}_1`,
          role: "human",
          content: "This is a placeholder for a real human message.",
          created_at: new Date(Date.now() - 60000).toISOString()
        },
        {
          id: `msg_live_${conversationId}_2`,
          role: "assistant",
          content: "This is a placeholder response from the live Anthropic API.",
          created_at: new Date().toISOString()
        }
      ];
      
      return {
        id: conversationId,
        created_at: new Date(Date.now() - 120000).toISOString(),
        messages: mockRealMessages
      };
      
    } catch (error) {
      console.error('Error interacting with Anthropic API:', error);
      console.log('Falling back to mock data');
      return this._getMockConversation(conversationId);
    }
  }
  
  /**
   * Generate mock conversation data with MCP-related content
   */
  _getMockConversation(conversationId) {
    if (typeof conversationId !== 'string') {
      console.warn('Invalid conversationId type:', typeof conversationId);
      // Generate a fallback ID if the input is not a string
      conversationId = 'conv_fallback_' + crypto.randomBytes(4).toString('hex');
    }
    
    // Generate a seed from the conversation ID for consistent mocks
    const seed = conversationId.split('_').pop().slice(0, 6);
    const now = Date.now();
    
    // Create timestamps for the conversation
    const timestamps = [
      new Date(now - 3600000).toISOString(),  // 1 hour ago
      new Date(now - 3550000).toISOString(),  // 59 minutes ago
      new Date(now - 1800000).toISOString(),  // 30 minutes ago
      new Date(now - 1750000).toISOString(),  // 29 minutes ago
      new Date(now - 900000).toISOString(),   // 15 minutes ago
      new Date(now - 850000).toISOString()    // 14 minutes ago
    ];
    
    // MCP-related topic messages
    const messages = [
      {
        id: `msg_${seed}_1`,
        role: "human",
        content: "Hello Claude, I'd like to discuss the Model Context Protocol.",
        created_at: timestamps[0]
      },
      {
        id: `msg_${seed}_2`,
        role: "assistant",
        content: "Hello! I'd be happy to discuss the Model Context Protocol (MCP). MCP is designed to create a standardized way for AI models to exchange context data with applications and other systems. What specific aspects would you like to explore?",
        created_at: timestamps[1]
      },
      {
        id: `msg_${seed}_3`,
        role: "human",
        content: "How does MCP help with data extraction from different sources?",
        created_at: timestamps[2]
      },
      {
        id: `msg_${seed}_4`,
        role: "assistant",
        content: "MCP helps with data extraction by providing a consistent format for context data across different sources. This means you can have extractors for various platforms (like Claude, GitHub, Cursor, etc.) that all output data in the same structured format. The benefits include:\n\n1. **Uniformity**: All extracted data follows the same schema\n2. **Traceability**: Every extraction operation has a unique context_id\n3. **Composability**: You can combine contexts from multiple sources\n4. **Extensibility**: Easy to add new data sources with the same interface\n\nThis makes it much easier to build systems that can work with multiple data sources without having to handle each one differently.",
        created_at: timestamps[3]
      }
    ];
    
    // Add additional messages based on the seed to make it more unique
    if (seed.charCodeAt(0) % 2 === 0) {
      messages.push(
        {
          id: `msg_${seed}_5`,
          role: "human",
          content: "Can you explain how context tracking works in MCP?",
          created_at: timestamps[4]
        },
        {
          id: `msg_${seed}_6`,
          role: "assistant",
          content: "Context tracking in MCP works through a simple but powerful mechanism:\n\n1. **Unique Context IDs**: Every context gets a unique identifier that persists throughout its lifecycle\n\n2. **Context Lineage**: When contexts are combined or transformed, child contexts retain references to their parent contexts\n\n3. **Metadata**: Each context includes metadata about its creation, source, and operations performed\n\n4. **Context Graph**: These relationships create a directed graph of contexts showing how information flows\n\nWith this approach, you can trace any piece of information back to its source and understand exactly how it was processed along the way. This is particularly useful for debugging, auditing, and building reliable AI systems where explainability is important.",
          created_at: timestamps[5]
        }
      );
    }
    
    return {
      id: conversationId,
      created_at: new Date(now - 3650000).toISOString(), // Just over an hour ago
      messages: messages
    };
  }
}

const generateUUID = () => crypto.randomUUID();

/**
 * Extract data from Claude conversation
 */
async function extractFromClaude(options = {}) {
  console.log(`Extracting Claude conversation:`, options);
  
  // Extract conversationId from options
  const conversationId = options.conversationId || ('conv_' + crypto.randomBytes(4).toString('hex'));
  
  // 1. Authentication
  const anthropicClient = new AnthropicAPI(ANTHROPIC_API_KEY);
  
  // 2 & 3. Discovery & Extraction
  const conversation = await anthropicClient.getConversation(conversationId);
  
  // 4. Transformation to MCP
  const mcpContext = {
    context_id: generateUUID(), // Use standard UUID
    operation: "extract",
    parameters: {
      source: "claude",
      conversationId: conversationId
    },
    result: {
      conversation_id: conversation.id,
      created_at: conversation.created_at,
      messages: conversation.messages.map(msg => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        timestamp: msg.created_at
      }))
    },
    metadata: {
      extractionTime: new Date().toISOString(),
      messageCount: conversation.messages.length,
      using_real_api: !anthropicClient.useMock
    }
  };
  
  console.log("Generated MCP context:", JSON.stringify(mcpContext, null, 2));
  
  // 5. Transmission to MCP endpoint
  return sendToMcpEndpoint(mcpContext);
}

/**
 * Send context to MCP endpoint
 */
async function sendToMcpEndpoint(mcpContext) {
  console.log(`Sending to MCP endpoint: ${MCP_ENDPOINT}`);
  
  const requestBody = {
    modelId: 'claude-extractor',
    context: mcpContext
  };
  
  try {
    const response = await fetch(MCP_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
      },
      body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
      throw new Error(`MCP endpoint error: ${response.status}`);
    }
    
    const result = await response.json();
    console.log("MCP Response:", JSON.stringify(result, null, 2));
    return result;
  } catch (error) {
    console.error("Error sending to MCP endpoint:", error.message);
    throw error;
  }
}

/**
 * Main execution
 */
async function main() {
  try {
    // Use a generated conversation ID
    const convId = "conv_" + crypto.randomBytes(4).toString('hex');
    console.log(`Using conversation ID: ${convId}`);
    
    const result = await extractFromClaude({ conversationId: convId });
    console.log("Extraction complete!");
  } catch (error) {
    console.error("Extraction failed:", error);
  }
}

// Run the extractor only if executed directly
if (require.main === module) {
  main();
}

// Export for use in the orchestrator
module.exports = {
  extractFromClaude,
  sendToMcpEndpoint,
  AnthropicAPI
}; 