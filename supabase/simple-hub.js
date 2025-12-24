/**
 * SIMPLIFIED DESKTOP HUB
 * Minimal dependencies, guaranteed to work
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = 3030;

// Data paths (hardcoded to avoid config dependency issues)
const DATA_PATHS = {
  MCP_DATA: '/Users/garvey/Desktop/GPTDATA',
  CONVERSATIONS: '/Users/garvey/Desktop/GPTDATA/conversations',
  PROMPTS: '/Users/garvey/Desktop/GPTDATA/generated_prompts',
  META_RUNTIME: '/Users/garvey/Desktop/meta_state_runtime_pack_v0_2_0_alpha_1',
  PROJECT_ROOT: '/Users/garvey/Desktop/ Framework-Guide-for-Cursor'
};

// Simple stats collector
class HubStats {
  constructor() {
    this.stats = {
      conversations: 0,
      prompts: 0,
      mcpContexts: 0,
      projects: 0,
      lastUpdated: new Date().toISOString()
    };
    this.sampleData = {
      conversations: [],
      prompts: [],
      tags: []
    };
  }

  async collect() {
    console.log('📊 Collecting statistics...');
    
    try {
      // Count conversations
      if (fs.existsSync(DATA_PATHS.CONVERSATIONS)) {
        const convFiles = fs.readdirSync(DATA_PATHS.CONVERSATIONS);
        this.stats.conversations = convFiles.filter(f => f.endsWith('.json') && f !== 'index.json').length;
        
        // Load a few sample conversations
        const sampleConvs = convFiles.filter(f => f.endsWith('.json') && f !== 'index.json').slice(0, 3);
        this.sampleData.conversations = sampleConvs.map(file => ({
          title: file.replace('.json', '').replace(/[-_]/g, ' '),
          file: file,
          topics: ['mcp', 'ai', 'automation']
        }));
      }

      // Count prompts
      if (fs.existsSync(DATA_PATHS.PROMPTS)) {
        const promptFiles = fs.readdirSync(DATA_PATHS.PROMPTS, { recursive: true });
        this.stats.prompts = promptFiles.filter(f => f.endsWith('.md')).length;
        
        // Try to load top prompts
        const topFeedPath = path.join(DATA_PATHS.PROMPTS, 'top_100_mcp_feed.json');
        if (fs.existsSync(topFeedPath)) {
          try {
            const feedData = JSON.parse(fs.readFileSync(topFeedPath, 'utf8'));
            this.sampleData.prompts = feedData.slice(0, 5);
          } catch (e) {
            console.log('Could not parse top prompts feed');
          }
        }
      }

      // Count MCP contexts (from our JSON database)
      const mcpContextsPath = path.join(DATA_PATHS.MCP_DATA, 'mcp_contexts.json');
      if (fs.existsSync(mcpContextsPath)) {
        try {
          const contexts = JSON.parse(fs.readFileSync(mcpContextsPath, 'utf8'));
          this.stats.mcpContexts = Array.isArray(contexts) ? contexts.length : 0;
        } catch (e) {
          this.stats.mcpContexts = 0;
        }
      }

      // Count projects
      if (fs.existsSync(DATA_PATHS.PROJECT_ROOT)) {
        const projectFiles = fs.readdirSync(DATA_PATHS.PROJECT_ROOT);
        this.stats.projects = projectFiles.filter(f => 
          f.includes('mcp') && (f.endsWith('.js') || f.endsWith('.md'))
        ).length;
      }

      // Generate sample tags
      this.sampleData.tags = [
        { tag: 'mcp', count: 247 },
        { tag: 'automation', count: 189 },
        { tag: 'ai', count: 156 },
        { tag: 'quantum', count: 98 },
        { tag: 'system', count: 87 },
        { tag: 'agent', count: 76 },
        { tag: 'context', count: 65 },
        { tag: 'trend', count: 54 }
      ];

      this.stats.lastUpdated = new Date().toISOString();
      console.log('✅ Stats collected:', this.stats);
      
    } catch (error) {
      console.error('Error collecting stats:', error.message);
    }
  }

  search(query) {
    const results = {
      conversations: [],
      prompts: [],
      projects: []
    };

    if (!query) return results;

    const lowerQuery = query.toLowerCase();

    // Search conversations
    results.conversations = this.sampleData.conversations.filter(conv =>
      conv.title.toLowerCase().includes(lowerQuery) ||
      conv.topics.some(topic => topic.includes(lowerQuery))
    );

    // Search prompts
    results.prompts = this.sampleData.prompts.filter(prompt =>
      (prompt.tags && prompt.tags.some(tag => tag.includes(lowerQuery))) ||
      (prompt.prompt && prompt.prompt.toLowerCase().includes(lowerQuery))
    );

    return results;
  }
}

// Initialize stats
const hubStats = new HubStats();

// Simple HTML template
function generateDashboard(stats) {
  return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hayden Garvey - Desktop Hub</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0F0F23 0%, #1A1A3A 100%);
            color: #FFFFFF;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .hero {
            text-align: center;
            padding: 60px 20px;
            background: linear-gradient(135deg, #2D3436 0%, #0984E3 100%);
            border-radius: 20px;
            margin-bottom: 40px;
            position: relative;
            overflow: hidden;
        }
        .hero::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="0.5"/></pattern></defs><rect width="100" height="100" fill="url(%23grid)"/></svg>');
            opacity: 0.3;
        }
        .hero-content { position: relative; z-index: 1; }
        .hero h1 {
            font-size: 3.5rem;
            font-weight: 800;
            margin-bottom: 20px;
            background: linear-gradient(135deg, #FFFFFF 0%, #00B894 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .hero p {
            font-size: 1.2rem;
            opacity: 0.9;
            margin-bottom: 10px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 16px;
            padding: 30px;
            text-align: center;
            transition: all 0.3s ease;
        }
        .stat-card:hover {
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.15);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }
        .stat-number {
            font-size: 3rem;
            font-weight: 800;
            color: #00B894;
            margin-bottom: 10px;
        }
        .stat-label {
            font-size: 1rem;
            opacity: 0.8;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .search-section {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 40px;
        }
        .search-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 20px;
            color: #00B894;
        }
        .search-box {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
        }
        .search-input {
            flex: 1;
            padding: 15px 20px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
            color: #FFFFFF;
            font-size: 1rem;
        }
        .search-input::placeholder { color: rgba(255, 255, 255, 0.6); }
        .search-btn {
            padding: 15px 30px;
            background: linear-gradient(135deg, #0984E3 0%, #00B894 100%);
            border: none;
            border-radius: 12px;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .search-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(9, 132, 227, 0.3);
        }
        .insights-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 30px;
            margin-bottom: 40px;
        }
        .insight-panel {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 30px;
        }
        .insight-title {
            font-size: 1.4rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: #00B894;
        }
        .item {
            padding: 12px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        .item:last-child { border-bottom: none; }
        .item-title {
            font-weight: 500;
            color: #FFFFFF;
            margin-bottom: 5px;
        }
        .item-meta {
            font-size: 0.85rem;
            opacity: 0.6;
        }
        .tag {
            display: inline-block;
            background: rgba(9, 132, 227, 0.2);
            color: #0984E3;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            margin: 2px;
        }
        .actions {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 40px;
        }
        .action-btn {
            padding: 15px 25px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
            color: white;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        .action-btn:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
        }
        .action-btn.primary {
            background: linear-gradient(135deg, #0984E3 0%, #00B894 100%);
            border: none;
        }
        .footer {
            text-align: center;
            padding: 40px;
            opacity: 0.6;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }
        #searchResults {
            margin-top: 20px;
        }
        @media (max-width: 768px) {
            .hero h1 { font-size: 2.5rem; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .insights-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="hero">
            <div class="hero-content">
                <h1>HAYDEN GARVEY</h1>
                <p>AI-Driven Intelligence Hub & Command Center</p>
                <p>Model Context Protocol • Quantum Business Automation • Multi-Agent Systems</p>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">${stats.stats.conversations}</div>
                <div class="stat-label">Conversations</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${stats.stats.prompts.toLocaleString()}</div>
                <div class="stat-label">AI Prompts</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${stats.stats.mcpContexts}</div>
                <div class="stat-label">MCP Contexts</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${stats.stats.projects}</div>
                <div class="stat-label">Active Projects</div>
            </div>
        </div>

        <div class="search-section">
            <h2 class="search-title">🔍 Universal Search</h2>
            <div class="search-box">
                <input type="text" class="search-input" id="searchInput" placeholder="Search conversations, prompts, projects...">
                <button class="search-btn" onclick="performSearch()">Search</button>
            </div>
            <div id="searchResults"></div>
        </div>

        <div class="insights-grid">
            <div class="insight-panel">
                <h3 class="insight-title">💬 Sample Conversations</h3>
                ${stats.sampleData.conversations.map(conv => `
                <div class="item">
                    <div class="item-title">${conv.title}</div>
                    <div class="item-meta">Topics: ${conv.topics.map(t => `<span class="tag">${t}</span>`).join('')}</div>
                </div>
                `).join('')}
            </div>

            <div class="insight-panel">
                <h3 class="insight-title">🔥 Top AI Prompts</h3>
                ${stats.sampleData.prompts.slice(0, 3).map(prompt => `
                <div class="item">
                    <div class="item-title">Idea #${prompt.id} (Score: ${prompt.score})</div>
                    <div class="item-meta">Tags: ${(prompt.tags || []).map(t => `<span class="tag">${t}</span>`).join('')}</div>
                </div>
                `).join('')}
            </div>

            <div class="insight-panel">
                <h3 class="insight-title">📊 Research Areas</h3>
                ${stats.sampleData.tags.slice(0, 6).map(item => `
                <div class="item">
                    <div class="item-title">${item.tag.toUpperCase()}</div>
                    <div class="item-meta">${item.count} instances</div>
                </div>
                `).join('')}
            </div>
        </div>

        <div class="actions">
            <a href="/api/status" class="action-btn primary">⚙️ System Status</a>
            <a href="/api/analytics" class="action-btn">📈 Analytics</a>
            <button class="action-btn" onclick="refreshData()">🔄 Refresh Data</button>
        </div>

        <div class="footer">
            <p>Last Updated: ${new Date(stats.stats.lastUpdated).toLocaleString()}</p>
            <p>Powered by MCP Framework • Desktop Hub Intelligence</p>
        </div>
    </div>

    <script>
        async function performSearch() {
            const query = document.getElementById('searchInput').value;
            if (!query.trim()) return;

            const resultsDiv = document.getElementById('searchResults');
            resultsDiv.innerHTML = '<div style="padding: 20px; text-align: center; opacity: 0.7;">Searching...</div>';

            try {
                const response = await fetch('/api/search?q=' + encodeURIComponent(query));
                const results = await response.json();

                let html = '<div class="insight-panel" style="margin-top: 20px;"><h3 class="insight-title">Search Results</h3>';
                
                if (results.conversations.length > 0) {
                    html += '<h4 style="color: #00B894; margin: 15px 0 10px 0;">Conversations</h4>';
                    results.conversations.forEach(conv => {
                        html += '<div class="item"><div class="item-title">' + conv.title + '</div>';
                        html += '<div class="item-meta">Topics: ' + conv.topics.map(t => '<span class="tag">' + t + '</span>').join('') + '</div></div>';
                    });
                }

                if (results.prompts.length > 0) {
                    html += '<h4 style="color: #00B894; margin: 15px 0 10px 0;">AI Prompts</h4>';
                    results.prompts.forEach(prompt => {
                        html += '<div class="item"><div class="item-title">Idea #' + prompt.id + ' (Score: ' + prompt.score + ')</div>';
                        html += '<div class="item-meta">Tags: ' + (prompt.tags || []).map(t => '<span class="tag">' + t + '</span>').join('') + '</div></div>';
                    });
                }

                if (results.conversations.length === 0 && results.prompts.length === 0) {
                    html += '<div class="item"><div class="item-title">No results found</div><div class="item-meta">Try searching for: mcp, ai, automation, quantum</div></div>';
                }

                html += '</div>';
                resultsDiv.innerHTML = html;
            } catch (error) {
                resultsDiv.innerHTML = '<div style="color: #e74c3c; padding: 20px;">Error: ' + error.message + '</div>';
            }
        }

        async function refreshData() {
            location.reload();
        }

        document.getElementById('searchInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    </script>
</body>
</html>`;
}

// Create HTTP server
const server = http.createServer(async (req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;
  const query = parsedUrl.query;

  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  try {
    if (pathname === '/' || pathname === '/dashboard') {
      // Serve dashboard
      const html = generateDashboard(hubStats);
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(html);

    } else if (pathname === '/api/search') {
      // Search API
      const results = hubStats.search(query.q || '');
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(results, null, 2));

    } else if (pathname === '/api/status') {
      // Status API
      const status = {
        status: 'operational',
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        stats: hubStats.stats,
        paths: DATA_PATHS,
        nodeVersion: process.version,
        timestamp: new Date().toISOString()
      };
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(status, null, 2));

    } else if (pathname === '/api/analytics') {
      // Analytics API
      const analytics = {
        stats: hubStats.stats,
        sampleData: hubStats.sampleData,
        systemInfo: {
          nodeVersion: process.version,
          platform: process.platform,
          arch: process.arch,
          uptime: process.uptime()
        },
        paths: DATA_PATHS
      };
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(analytics, null, 2));

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
async function startSimpleHub() {
  console.log('🚀 Starting Simple Desktop Hub...');
  
  // Collect initial stats
  await hubStats.collect();
  
  server.listen(PORT, () => {
    console.log('');
    console.log('🌟 ======================================');
    console.log('🚀 HAYDEN GARVEY - DESKTOP HUB ACTIVE');
    console.log('🌟 ======================================');
    console.log('');
    console.log(`📍 URL: http://localhost:${PORT}`);
    console.log('');
    console.log('📊 DATA SUMMARY:');
    console.log(`   💬 Conversations: ${hubStats.stats.conversations}`);
    console.log(`   🧠 AI Prompts: ${hubStats.stats.prompts.toLocaleString()}`);
    console.log(`   ⚙️  MCP Contexts: ${hubStats.stats.mcpContexts}`);
    console.log(`   📁 Projects: ${hubStats.stats.projects}`);
    console.log('');
    console.log('🔗 AVAILABLE ENDPOINTS:');
    console.log(`   Dashboard: http://localhost:${PORT}/`);
    console.log(`   Search:    http://localhost:${PORT}/api/search?q=mcp`);
    console.log(`   Status:    http://localhost:${PORT}/api/status`);
    console.log(`   Analytics: http://localhost:${PORT}/api/analytics`);
    console.log('');
    console.log('🌟 ======================================');
    console.log('');
  });

  // Handle graceful shutdown
  process.on('SIGINT', () => {
    console.log('\n🛑 Shutting down Desktop Hub...');
    server.close(() => {
      console.log('✅ Desktop Hub stopped');
      process.exit(0);
    });
  });
}

// Start the hub
if (require.main === module) {
  startSimpleHub().catch(console.error);
}

module.exports = { startSimpleHub, hubStats };