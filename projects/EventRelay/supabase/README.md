# Model Context Protocol (MCP) Framework

The Model Context Protocol (MCP) Framework is a standardized way for AI models to exchange context data with applications and systems. It acts like USB-C for AI systems, creating secure, two-way connections between external data sources and AI/LLM systems.

## Features

- **Universal Context Format**: Standardized format for all data sources and AI systems
- **Bidirectional Communication**: Two-way context sharing between systems
- **Multiple Extractors**: Pre-built extractors for common data sources:
  - **Claude**: Extract conversation data from Claude
  - **GitHub**: Extract repo data, commits, and files
  - **Cursor/VSCode**: Extract workspace structure and code
  - **SQL**: Extract database query results and schema
  - **Document**: Extract content from PDFs and other document types
- **Context Persistence**: Automatic saving to Supabase with configurable policies
- **Access Control**: Public/private contexts with team sharing
- **Visualization**: Interactive visualization of context relationships
- **Analytics**: Built-in analysis of context patterns and relationships

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-framework.git
cd mcp-framework

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your Supabase credentials
```

## Quick Start

```javascript
const { MCPOrchestrator } = require('./mcp-orchestrator');

// Create orchestrator instance
const orchestrator = new MCPOrchestrator();

// Extract data from Claude
const claudeContext = await orchestrator.extract('claude', { 
  conversationId: 'your-conversation-id' 
});

// Extract data from GitHub
const githubContext = await orchestrator.extract('github', {
  repoPath: 'owner/repo',
  branch: 'main'
});

// Combine contexts
const combinedContext = await orchestrator.combineContexts([
  claudeContext.context_id,
  githubContext.context_id
]);

// Generate visualization
orchestrator.generateVisualization('./mcp-visualization.html');
```

## Extractors

### Claude Extractor

```javascript
// Extract from Claude
const claudeContext = await orchestrator.extract('claude', { 
  conversationId: 'your-conversation-id'
});
```

### GitHub Extractor

```javascript
// Extract from GitHub
const githubContext = await orchestrator.extract('github', {
  repoPath: 'owner/repo',
  branch: 'main',
  path: 'optional/path/to/file/or/directory'
});
```

### Cursor/VSCode Extractor

```javascript
// Extract from workspace
const cursorContext = await orchestrator.extract('cursor', {
  workspacePath: '/path/to/workspace',
  includeFiles: ['*.js', '*.ts'],
  excludeFiles: ['node_modules/**'],
  includeGitInfo: true,
  includeFileContents: true
});
```

### SQL Extractor

```javascript
// Extract from SQL query results
const sqlContext = await orchestrator.extract('sql', {
  query: 'SELECT * FROM users WHERE status = "active"',
  results: [/* query results */],
  connection: {
    host: 'localhost',
    database: 'mydb',
    user: 'username'
  }
});
```

### Document Extractor

```javascript
// Extract from document
const documentContext = await orchestrator.extract('document', {
  filePath: '/path/to/document.pdf',
  extractMetadata: true,
  extractStructure: true
});
```

## Persistence and Access Control

The MCP Framework automatically persists contexts to Supabase with configurable access control:

```javascript
// Create private context with team access
const privateContext = await orchestrator.extract('claude', { 
  conversationId: 'conv123',
  accessControl: {
    isPublic: false,
    ownerUserId: 'user-123',
    teamAccess: ['team-456']
  }
});

// Create public context
const publicContext = await orchestrator.extract('github', { 
  repoPath: 'org/repo',
  accessControl: {
    isPublic: true
  }
});

// Configure persistence
const orchestrator = new MCPOrchestrator({
  persistence: {
    enabled: true,
    autoRetry: true,
    maxRetries: 3,
    retryDelay: 1000,
    conditionalPersist: (context) => {
      // Only persist non-temporary contexts
      return context.operation !== 'temp';
    }
  }
});
```

## Persistence Options

The MCP Framework offers flexible persistence options for storing contexts:

### 1. Supabase (Cloud Persistence)

By default, the framework attempts to use Supabase for cloud-based persistence:

```javascript
// Configure Supabase connection
const orchestrator = new MCPOrchestrator({
  persistence: {
    enabled: true,
    autoRetry: true,
    maxRetries: 3,
    retryDelay: 1000
  }
});
```

This requires:
- A Supabase account and project
- The `supabase_setup.sql` script run on your Supabase instance
- Environment variables in `.env.local`:
  ```
  NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
  NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_key
  ```

### 2. SQLite (Local Persistence)

If Supabase is unavailable or fails, the framework automatically falls back to SQLite for local persistence:

```javascript
// The fallback happens automatically, but you can configure it:
const orchestrator = new MCPOrchestrator({
  persistence: {
    enabled: true,
    fallbackToSqlite: true, // Enable SQLite fallback (default: true)
    sqlitePath: './my-custom-db.db' // Custom SQLite database path
  }
});
```

### 3. File Export (Manual Persistence)

For manual persistence, you can export contexts to a file:

```javascript
// Export all contexts to a JSON file
orchestrator.exportContextsToFile('./mcp-contexts.json');

// Later, load them back
const newOrchestrator = new MCPOrchestrator();
newOrchestrator.importContextsFromFile('./mcp-contexts.json');
```

## SQL Integration Testing

The MCP Framework includes a comprehensive SQL integration test suite to verify database connectivity and MCP context extraction:

```bash
# Set up PostgreSQL environment variables
./setup_postgres_local.sh

# Run the SQL integration test
npm run test-sql
```

The SQL integration test:
1. Connects to a PostgreSQL database
2. Creates a test table with sample data
3. Runs multiple SQL queries (simple SELECT, aggregation, schema information)
4. Extracts MCP context from each query result
5. Combines the contexts
6. Generates a visualization of the SQL contexts

For detailed documentation on SQL integration, see [MCP-SQL-INTEGRATION.md](MCP-SQL-INTEGRATION.md).

## Visualization

Visualize context relationships with the built-in visualizer:

```javascript
// Generate HTML visualization
orchestrator.generateVisualization('./mcp-visualization.html');

// Export contexts to file
orchestrator.exportContextsToFile('./mcp-contexts.json');

// Analyze contexts
const analytics = orchestrator.analyzeContexts();
console.log(analytics);
```

## Supabase MCP Integration

The MCP Framework can be used directly with Supabase using the official Supabase MCP server. This allows your AI tools to interact with your Supabase projects directly.

### Setup Instructions

Run the included setup script:

```bash
./setup_supabase_mcp.sh
```

This will:
1. Create necessary configuration files for Cursor, VS Code, and Claude
2. Guide you through creating a Supabase personal access token
3. Help you configure the MCP integration for your AI tools

### Supported AI Tools

The MCP Framework works with the following AI tools via Supabase MCP:

- **Cursor** - Use `.cursor/mcp.json` configuration
- **Visual Studio Code (Copilot)** - Use `.vscode/mcp.json` configuration
- **Windsurf (Codium)** - Use `.cursor/mcp.json` configuration
- **Claude Desktop/Code** - Use `.mcp.json` in the project root
- **Cline (VS Code extension)** - Use the MCP Servers configuration

### Using MCP with Local Supabase

For local Supabase instances, use the Postgres MCP server:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://postgres:postgres@localhost:5432/postgres"]
    }
  }
}
```

Replace the connection string with your actual database URL (get it via `supabase status`).

## Enterprise Features

For enterprise usage, the MCP Framework provides:

- **Team Collaboration**: Share contexts across teams securely
- **Audit Trail**: Complete history of context operations
- **Retry Mechanisms**: Automatic retry for failed operations
- **Error Handling**: Robust error reporting and recovery
- **Monitoring**: Performance and usage analytics

## Testing

Run the comprehensive test suite to verify all MCP Framework functionality:

```bash
# Test all extractors and features
node test_full_mcp_framework.js

# Test SQL integration specifically
npm run test-sql

# Test Supabase integration
npm run test-real
```

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Troubleshooting: Environment File Creation Blocked

If you encounter issues where `.env.local` (in `mcp-supabase-frontend/`) or `~/.config/supabase-mcp/.env` cannot be created or edited automatically, please create them manually with the following content:

```
# For mcp-supabase-frontend/.env.local
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
MCP_ACCESS_TOKEN=your_mcp_access_token
```

```
# For ~/.config/supabase-mcp/.env
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
MCP_ACCESS_TOKEN=your_mcp_access_token
```

Replace the values with your actual Supabase project credentials and MCP access token. If you need help obtaining these, refer to the MCP-SUPABASE-INTEGRATION.md guide. 