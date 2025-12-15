# MCP-researcher Server

Your own research assistant inside of Claude! Utilizes Perplexity's Sonar Pro API to get documentation, create up-to-date API routes, and check deprecated code. Includes Chain of Thought Reasoning and local chat history through SQLite.

<a href="https://glama.ai/mcp/servers/g1i6ilg8sl"><img width="380" height="200" src="https://glama.ai/mcp/servers/g1i6ilg8sl/badge" alt="MCP-researcher Server MCP server" /></a>

## Features

### 1. Search
Performs general search queries to get comprehensive information on any topic. Supports different detail levels (brief, normal, detailed) to get tailored responses.

### 2. Get Documentation
Retrieves documentation and usage examples for specific technologies, libraries, or APIs. Get comprehensive documentation including best practices and common pitfalls.

### 3. Find APIs
Discovers and evaluates APIs that could be integrated into a project. Get detailed analysis of features, pricing, and integration complexity.

### 4. Check Deprecated Code
Analyzes code for deprecated features or patterns, providing migration guidance. Helps modernize code by suggesting current best practices.

## Prerequisites

1. **System Requirements**:
   - Node.js (install from [nodejs.org](https://nodejs.org))
   - Python with distutils (required for some npm dependencies)
     ```bash
     # On macOS with Homebrew:
     brew install python-setuptools
     ```

2. **API Key**:
   - Get your Perplexity API key from [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)

## Installation

1. **Create Project Directory**:
   ```bash
   mkdir -p ~/Documents/Claude/MCP
   cd ~/Documents/Claude/MCP
   ```

2. **Clone the Repository**:
   ```bash
   git clone https://github.com/pashpashpash/perplexity-mcp.git
   cd perplexity-mcp
   ```

3. **Install Dependencies**:
   ```bash
   npm install
   ```
   Note: If you see Python distutils errors, make sure you've installed python-setuptools as mentioned in prerequisites.

4. **Build the Project**:
   ```bash
   npm run build
   ```
   This will create the build directory with the compiled server code.

## Configuration

1. **Configure Claude Desktop**:

Add this to your claude_desktop_config.json:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "perplexity-server": {
      "command": "node",
      "args": ["path/to/perplexity-mcp/build/index.js"],
      "env": {
        "PERPLEXITY_API_KEY": "your-api-key-here"
      },
      "autoApprove": [
        "search",
        "get_documentation",
        "find_apis",
        "check_deprecated_code"
      ]
    }
  }
}
```
Note: 
- Replace "path/to/perplexity-mcp" with the absolute path to your cloned repository
- Replace "your-api-key-here" with your Perplexity API key
- Make sure to use "/build/index.js" (not "/dist/index.js")

## Starting the Server

1. **Manual Start**:
   ```bash
   cd path/to/perplexity-mcp
   PERPLEXITY_API_KEY="your-api-key-here" node build/index.js
   ```

2. **Verify Server**:
   The server should start without any errors. Keep this terminal window open while using the server.

## Example Usage

### Search
```json
{
  "query": "What are the best practices for React hooks?",
  "detail_level": "detailed"
}
```

### Get Documentation
```json
{
  "technology": "React",
  "topic": "useEffect hook",
  "include_examples": true
}
```

### Find APIs
```json
{
  "category": "payment processing",
  "requirements": ["recurring billing", "international support"]
}
```

### Check Deprecated Code
```json
{
  "code": "class MyComponent extends React.Component {...}",
  "framework": "React",
  "version": "18"
}
```

## Troubleshooting

1. **Build Directory Issues**:
   - Make sure you're using the correct path in Claude Desktop config
   - Verify the build directory exists after running `npm run build`
   - Check that the path is using `/build/index.js`, not `/dist/index.js`

2. **Server Connection Issues**:
   - Ensure the server is running in a separate terminal
   - Verify the API key is properly set in the environment
   - Check Claude Desktop's MCP logs:
     ```bash
     tail -n 20 -f ~/Library/Logs/Claude/mcp*.log
     ```

3. **Python Dependencies**:
   - If you see Python distutils errors during npm install:
     ```bash
     brew install python-setuptools
     ```
   - Then retry `npm install`

## Development

```bash
# Install dependencies
npm install

# Build the project
npm run build

# Development with auto-rebuild
npm run watch

# Start server with debug output
DEBUG=* node build/index.js
```

## Documentation

For detailed examples and usage guides, see:
- [Search Examples](https://github.com/DaInfernalCoder/perplexity-mcp/blob/main/examples/search.md)
- [API Documentation Examples](https://github.com/DaInfernalCoder/perplexity-mcp/blob/main/examples/find-apis.md)
- [Deprecated Code Examples](https://github.com/DaInfernalCoder/perplexity-mcp/blob/main/examples/check-deprecated-code.md)

## License

MIT

---
Note: This is a fork of the [original perplexity-mcp repository](https://github.com/DaInfernalCoder/perplexity-mcp).
