/**
 * HAYDEN GARVEY - DESKTOP HUB
 * 
 * Unified Command Center & Intelligence Platform
 * Integrating MCP Framework + GPTDATA Repository + AI Workflows
 */

const express = require('express');
const fs = require('fs-extra');
const path = require('path');
const { DATA_PATHS, API_KEYS } = require('./lib/config');
const { supabase } = require('./lib/supabase');
const { MCPOrchestrator } = require('./mcp-orchestrator');

const app = express();
const PORT = process.env.PORT || 3030;

// Configure middleware
app.use(express.json({ limit: '50mb' }));
app.use(express.static(path.join(__dirname, 'hub-public')));
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'hub-views'));

// Initialize MCP Orchestrator
const orchestrator = new MCPOrchestrator({ visualize: true });

/**
 * DESKTOP HUB DATA AGGREGATOR
 * Combines MCP Framework + GPTDATA + Runtime Intelligence
 */
class DesktopHubIntelligence {
  constructor() {
    this.conversationCache = new Map();
    this.promptCache = new Map();
    this.projectCache = new Map();
    this.stats = {
      conversations: 0,
      prompts: 0,
      mcpContexts: 0,
      projects: 0,
      lastUpdated: new Date().toISOString()
    };
  }

  async initialize() {
    console.log('🚀 Initializing Desktop Hub Intelligence...');
    
    await Promise.all([
      this.loadConversations(),
      this.loadPrompts(),
      this.loadMcpData(),
      this.scanProjects()
    ]);
    
    console.log('✅ Desktop Hub Intelligence ready');
    console.log('📊 Stats:', this.stats);
  }

  async loadConversations() {
    try {
      const convDir = DATA_PATHS.CONVERSATIONS;
      const files = await fs.readdir(convDir);
      const jsonFiles = files.filter(f => f.endsWith('.json') && f !== 'index.json');
      
      for (const file of jsonFiles.slice(0, 50)) { // Limit for performance
        const filePath = path.join(convDir, file);
        const data = await fs.readJSON(filePath);
        
        this.conversationCache.set(data.id || file, {
          id: data.id || file,
          title: data.title || file.replace('.json', ''),
          created: data.created,
          updated: data.updated,
          messageCount: data.messages?.length || 0,
          topics: this.extractTopics(data),
          file: file
        });
      }
      
      this.stats.conversations = this.conversationCache.size;
    } catch (error) {
      console.error('Error loading conversations:', error.message);
    }
  }

  async loadPrompts() {
    try {
      const promptsDir = DATA_PATHS.PROMPTS;
      const topFeedPath = path.join(promptsDir, 'top_100_mcp_feed.json');
      
      if (await fs.pathExists(topFeedPath)) {
        const topPrompts = await fs.readJSON(topFeedPath);
        
        topPrompts.forEach(prompt => {
          this.promptCache.set(prompt.id, {
            id: prompt.id,
            score: prompt.score,
            tags: prompt.tags,
            files: prompt.files,
            prompt: prompt.prompt
          });
        });
      }
      
      // Count all prompt files
      const allPrompts = await fs.readdir(promptsDir, { recursive: true });
      this.stats.prompts = allPrompts.filter(f => f.endsWith('.md')).length;
      
    } catch (error) {
      console.error('Error loading prompts:', error.message);
    }
  }

  async loadMcpData() {
    try {
      const { data: contexts } = await supabase.from('mcp_contexts').select('*');
      const { data: projects } = await supabase.from('projects').select('*');
      
      this.stats.mcpContexts = contexts?.length || 0;
      this.stats.projects = projects?.length || 0;
      
    } catch (error) {
      console.error('Error loading MCP data:', error.message);
    }
  }

  async scanProjects() {
    try {
      const projectRoot = DATA_PATHS.PROJECT_ROOT;
      const files = await fs.readdir(projectRoot);
      
      // Identify key project files
      const projectFiles = files.filter(f => 
        f.endsWith('.js') || 
        f.endsWith('.md') || 
        f.endsWith('.json')
      );
      
      for (const file of projectFiles.slice(0, 20)) {
        if (file.includes('mcp') || file.includes('extractor')) {
          this.projectCache.set(file, {
            name: file,
            type: path.extname(file),
            path: path.join(projectRoot, file),
            category: this.categorizeProject(file)
          });
        }
      }
      
    } catch (error) {
      console.error('Error scanning projects:', error.message);
    }
  }

  extractTopics(conversation) {
    const content = JSON.stringify(conversation).toLowerCase();
    const topics = [];
    
    const patterns = [
      'mcp', 'quantum', 'ai', 'automation', 'agent', 'system',
      'business', 'portfolio', 'api', 'database', 'integration',
      'protocol', 'architecture', 'framework', 'analytics'
    ];
    
    patterns.forEach(pattern => {
      if (content.includes(pattern)) {
        topics.push(pattern);
      }
    });
    
    return topics;
  }

  categorizeProject(filename) {
    if (filename.includes('extractor')) return 'extractor';
    if (filename.includes('orchestrator')) return 'orchestrator';
    if (filename.includes('test')) return 'test';
    if (filename.includes('setup')) return 'setup';
    if (filename.includes('mcp')) return 'mcp-core';
    return 'utility';
  }

  search(query, type = 'all') {
    const results = {
      conversations: [],
      prompts: [],
      projects: []
    };
    
    const lowerQuery = query.toLowerCase();
    
    if (type === 'all' || type === 'conversations') {
      for (const [id, conv] of this.conversationCache) {
        if (conv.title.toLowerCase().includes(lowerQuery) ||
            conv.topics.some(topic => topic.includes(lowerQuery))) {
          results.conversations.push(conv);
        }
      }
    }
    
    if (type === 'all' || type === 'prompts') {
      for (const [id, prompt] of this.promptCache) {
        if (prompt.tags.some(tag => tag.includes(lowerQuery)) ||
            prompt.prompt.toLowerCase().includes(lowerQuery)) {
          results.prompts.push(prompt);
        }
      }
    }
    
    if (type === 'all' || type === 'projects') {
      for (const [name, project] of this.projectCache) {
        if (project.name.toLowerCase().includes(lowerQuery) ||
            project.category.includes(lowerQuery)) {
          results.projects.push(project);
        }
      }
    }
    
    return results;
  }

  getTopInsights() {
    const topPrompts = Array.from(this.promptCache.values())
      .sort((a, b) => b.score - a.score)
      .slice(0, 10);
    
    const recentConversations = Array.from(this.conversationCache.values())
      .sort((a, b) => (b.updated || 0) - (a.updated || 0))
      .slice(0, 5);
    
    const topTags = {};
    this.promptCache.forEach(prompt => {
      prompt.tags.forEach(tag => {
        topTags[tag] = (topTags[tag] || 0) + 1;
      });
    });
    
    return {
      topPrompts,
      recentConversations,
      topTags: Object.entries(topTags)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 10)
        .map(([tag, count]) => ({ tag, count }))
    };
  }
}

// Initialize Intelligence System
const intelligence = new DesktopHubIntelligence();

// ROUTES

// Main Dashboard
app.get('/', async (req, res) => {
  const insights = intelligence.getTopInsights();
  const stats = intelligence.stats;
  
  res.render('dashboard', {
    title: 'Hayden Garvey - Desktop Hub',
    stats,
    insights,
    timestamp: new Date().toISOString()
  });
});

// Search API
app.get('/api/search', async (req, res) => {
  const { q: query, type = 'all' } = req.query;
  
  if (!query) {
    return res.json({ error: 'Query parameter required' });
  }
  
  const results = intelligence.search(query, type);
  res.json(results);
});

// Conversation Details
app.get('/api/conversation/:id', async (req, res) => {
  const conversation = intelligence.conversationCache.get(req.params.id);
  
  if (!conversation) {
    return res.status(404).json({ error: 'Conversation not found' });
  }
  
  // Load full conversation data
  try {
    const fullData = await fs.readJSON(path.join(DATA_PATHS.CONVERSATIONS, conversation.file));
    res.json(fullData);
  } catch (error) {
    res.status(500).json({ error: 'Failed to load conversation' });
  }
});

// Prompt Details
app.get('/api/prompt/:id', async (req, res) => {
  const prompt = intelligence.promptCache.get(parseInt(req.params.id));
  
  if (!prompt) {
    return res.status(404).json({ error: 'Prompt not found' });
  }
  
  res.json(prompt);
});

// MCP Operations
app.post('/api/mcp/extract', async (req, res) => {
  const { source, parameters } = req.body;
  
  try {
    const result = await orchestrator.extract(source, parameters);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Data Discovery
app.post('/api/discover', async (req, res) => {
  try {
    // Trigger MCP discovery
    const { supabase } = require('./lib/supabase');
    const response = await fetch('/api/search?discover_mcps=true&query=*');
    
    // Refresh intelligence cache
    await intelligence.initialize();
    
    res.json({ 
      success: true, 
      stats: intelligence.stats,
      message: 'Data discovery completed' 
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Analytics Dashboard
app.get('/api/analytics', async (req, res) => {
  const insights = intelligence.getTopInsights();
  const projectDistribution = {};
  
  intelligence.projectCache.forEach(project => {
    projectDistribution[project.category] = (projectDistribution[project.category] || 0) + 1;
  });
  
  res.json({
    ...insights,
    projectDistribution,
    stats: intelligence.stats
  });
});

// System Status
app.get('/api/status', async (req, res) => {
  res.json({
    status: 'operational',
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    stats: intelligence.stats,
    paths: DATA_PATHS,
    timestamp: new Date().toISOString()
  });
});

// Initialize and start server
async function startHub() {
  try {
    // Create required directories
    await fs.ensureDir(path.join(__dirname, 'hub-public'));
    await fs.ensureDir(path.join(__dirname, 'hub-views'));
    
    // Initialize intelligence system
    await intelligence.initialize();
    
    app.listen(PORT, () => {
      console.log('🌟 ====================================');
      console.log('🚀 HAYDEN GARVEY - DESKTOP HUB ACTIVE');
      console.log('🌟 ====================================');
      console.log(`📍 URL: http://localhost:${PORT}`);
      console.log(`📊 Conversations: ${intelligence.stats.conversations}`);
      console.log(`🧠 Prompts: ${intelligence.stats.prompts}`);
      console.log(`⚙️  MCP Contexts: ${intelligence.stats.mcpContexts}`);
      console.log(`📁 Projects: ${intelligence.stats.projects}`);
      console.log('🌟 ====================================');
    });
    
  } catch (error) {
    console.error('❌ Failed to start Desktop Hub:', error);
    process.exit(1);
  }
}

// Export for external use
module.exports = { app, intelligence, startHub };

// Start if run directly
if (require.main === module) {
  startHub();
}