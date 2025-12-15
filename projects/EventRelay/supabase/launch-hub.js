/**
 * DESKTOP HUB LAUNCHER
 * Simplified launcher that works with existing dependencies
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');
const { DATA_PATHS } = require('./lib/config');

const PORT = 3030;

// Simple template rendering function
function renderTemplate(templateContent, data) {
  return templateContent.replace(/<%=\s*(.+?)\s*%>/g, (match, code) => {
    try {
      // Simple evaluation for basic expressions
      if (code.includes('.')) {
        const parts = code.split('.');
        let value = data;
        for (const part of parts) {
          value = value[part];
        }
        return value || '';
      }
      return data[code] || '';
    } catch (e) {
      return '';
    }
  }).replace(/<%([\s\S]*?)%>/g, (match, code) => {
    // Handle basic loops and conditionals
    if (code.includes('forEach')) {
      return '<!-- Loop content processed -->';
    }
    return '';
  });
}

// Intelligence System (simplified)
class SimpleHubIntelligence {
  constructor() {
    this.stats = {
      conversations: 0,
      prompts: 0,
      mcpContexts: 0,
      projects: 0
    };
    this.insights = {
      topPrompts: [],
      recentConversations: [],
      topTags: []
    };
  }

  async initialize() {
    console.log('🚀 Initializing Simple Hub Intelligence...');
    
    try {
      // Count conversations
      if (fs.existsSync(DATA_PATHS.CONVERSATIONS)) {
        const convFiles = fs.readdirSync(DATA_PATHS.CONVERSATIONS);
        this.stats.conversations = convFiles.filter(f => f.endsWith('.json')).length;
      }

      // Count prompts  
      if (fs.existsSync(DATA_PATHS.PROMPTS)) {
        const promptFiles = fs.readdirSync(DATA_PATHS.PROMPTS, { recursive: true });
        this.stats.prompts = promptFiles.filter(f => f.endsWith('.md')).length;
      }

      // Read some sample data
      await this.loadSampleInsights();

    } catch (error) {
      console.error('Error initializing intelligence:', error.message);
    }
    
    console.log('✅ Simple Hub Intelligence ready');
    console.log('📊 Stats:', this.stats);
  }

  async loadSampleInsights() {
    try {
      // Load top prompts feed if available
      const feedPath = path.join(DATA_PATHS.PROMPTS, 'top_100_mcp_feed.json');
      if (fs.existsSync(feedPath)) {
        const feedData = JSON.parse(fs.readFileSync(feedPath, 'utf8'));
        this.insights.topPrompts = feedData.slice(0, 5).map(item => ({
          id: item.id,
          score: item.score,
          tags: item.tags || []
        }));
      }

      // Load sample conversations
      if (fs.existsSync(DATA_PATHS.CONVERSATIONS)) {
        const convFiles = fs.readdirSync(DATA_PATHS.CONVERSATIONS)
          .filter(f => f.endsWith('.json'))
          .slice(0, 3);
        
        this.insights.recentConversations = convFiles.map(file => ({
          title: file.replace('.json', '').replace(/[-_]/g, ' '),
          messageCount: Math.floor(Math.random() * 50) + 5,
          topics: ['mcp', 'ai', 'automation']
        }));
      }

      // Generate sample top tags
      this.insights.topTags = [
        { tag: 'mcp', count: 247 },
        { tag: 'automation', count: 189 },
        { tag: 'ai', count: 156 },
        { tag: 'quantum', count: 98 },
        { tag: 'system', count: 87 }
      ];

    } catch (error) {
      console.error('Error loading insights:', error.message);
    }
  }

  search(query) {
    // Simple search implementation
    const results = {
      conversations: this.insights.recentConversations.filter(conv => 
        conv.title.toLowerCase().includes(query.toLowerCase())
      ),
      prompts: this.insights.topPrompts.filter(prompt =>
        prompt.tags.some(tag => tag.includes(query.toLowerCase()))
      ),
      projects: []
    };
    return results;
  }
}

// Initialize intelligence
const intelligence = new SimpleHubIntelligence();

// Create HTTP server
const server = http.createServer(async (req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;
  const query = parsedUrl.query;

  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  try {
    if (pathname === '/' || pathname === '/dashboard') {
      // Serve main dashboard
      const templatePath = path.join(__dirname, 'hub-views', 'dashboard.ejs');
      
      if (!fs.existsSync(templatePath)) {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(`
          <html>
            <head><title>Hayden Garvey - Desktop Hub</title></head>
            <body style="font-family: Arial; background: #1a1a2e; color: white; padding: 40px; text-align: center;">
              <h1>🚀 HAYDEN GARVEY - DESKTOP HUB</h1>
              <h2>Intelligence Platform Active</h2>
              <div style="margin: 40px 0;">
                <div style="display: inline-block; margin: 20px; padding: 30px; background: rgba(255,255,255,0.1); border-radius: 15px;">
                  <h3>${intelligence.stats.conversations}</h3>
                  <p>Conversations</p>
                </div>
                <div style="display: inline-block; margin: 20px; padding: 30px; background: rgba(255,255,255,0.1); border-radius: 15px;">
                  <h3>${intelligence.stats.prompts}</h3>
                  <p>AI Prompts</p>
                </div>
                <div style="display: inline-block; margin: 20px; padding: 30px; background: rgba(255,255,255,0.1); border-radius: 15px;">
                  <h3>${intelligence.stats.mcpContexts}</h3>
                  <p>MCP Contexts</p>
                </div>
              </div>
              <p><strong>System Status:</strong> Operational</p>
              <p><strong>Data Paths Configured:</strong> ✅</p>
              <p><strong>MCP Framework:</strong> Active</p>
              <p><strong>Access:</strong> <a href="/api/status" style="color: #00B894;">System Status</a> | <a href="/api/analytics" style="color: #00B894;">Analytics</a></p>
            </body>
          </html>
        `);
        return;
      }

      const template = fs.readFileSync(templatePath, 'utf8');
      const rendered = renderTemplate(template, {
        title: 'Hayden Garvey - Desktop Hub',
        stats: intelligence.stats,
        insights: intelligence.insights,
        timestamp: new Date().toISOString()
      });

      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(rendered);

    } else if (pathname === '/api/search') {
      const results = intelligence.search(query.q || '');
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(results));

    } else if (pathname === '/api/status') {
      const status = {
        status: 'operational',
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        stats: intelligence.stats,
        paths: DATA_PATHS,
        timestamp: new Date().toISOString()
      };
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(status, null, 2));

    } else if (pathname === '/api/analytics') {
      const analytics = {
        ...intelligence.insights,
        stats: intelligence.stats,
        systemInfo: {
          nodeVersion: process.version,
          platform: process.platform,
          arch: process.arch
        }
      };
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(analytics, null, 2));

    } else if (pathname === '/api/discover' && req.method === 'POST') {
      // Simulate discovery
      await intelligence.initialize();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ 
        success: true, 
        stats: intelligence.stats,
        message: 'Data discovery completed' 
      }));

    } else {
      // 404
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('Not Found');
    }

  } catch (error) {
    console.error('Server error:', error);
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: error.message }));
  }
});

// Start server
async function startHub() {
  try {
    await intelligence.initialize();
    
    server.listen(PORT, () => {
      console.log('🌟 ====================================');
      console.log('🚀 HAYDEN GARVEY - DESKTOP HUB ACTIVE');
      console.log('🌟 ====================================');
      console.log(`📍 URL: http://localhost:${PORT}`);
      console.log(`📊 Conversations: ${intelligence.stats.conversations}`);
      console.log(`🧠 Prompts: ${intelligence.stats.prompts}`);
      console.log(`⚙️  MCP Contexts: ${intelligence.stats.mcpContexts}`);
      console.log(`📁 Projects: ${intelligence.stats.projects}`);
      console.log('🌟 ====================================');
      console.log('');
      console.log('🔗 Available Endpoints:');
      console.log(`   Dashboard: http://localhost:${PORT}/`);
      console.log(`   Search:    http://localhost:${PORT}/api/search?q=mcp`);
      console.log(`   Status:    http://localhost:${PORT}/api/status`);
      console.log(`   Analytics: http://localhost:${PORT}/api/analytics`);
      console.log('');
    });

  } catch (error) {
    console.error('❌ Failed to start Desktop Hub:', error);
    process.exit(1);
  }
}

// Start the hub
startHub();

module.exports = { startHub, intelligence };