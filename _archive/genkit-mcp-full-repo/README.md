# Genkit MCP Server

This is an implementation of the [Genkit MCP](https://github.com/firebase/genkit/tree/HEAD/js/plugins/mcp) server, which provides integration between Genkit and the [Model Context Protocol](https://modelcontextprotocol.io) (MCP).

## Overview

This MCP server exposes several tools and prompts that can be used by MCP clients:

### Tools

1. **calculate** - Perform basic arithmetic operations
   - Operations: add, subtract, multiply, divide
   - Example: `{ "operation": "add", "a": 42, "b": 58 }`

2. **transform_text** - Transform text using various operations
   - Transformations: uppercase, lowercase, capitalize, reverse
   - Example: `{ "text": "hello world", "transformation": "uppercase" }`

### Prompts

1. **greeting** - Generate a friendly greeting
   - Parameters: name, time_of_day (morning, afternoon, evening, night)
   - Example: `{ "name": "User", "time_of_day": "evening" }`

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```

## Configuration

The server is configured in the Cline MCP settings file at:
`/Users/garvey/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

The configuration entry is:

```json
"github.com/firebase/genkit/tree/HEAD/js/plugins/mcp": {
  "command": "node",
  "args": [
    "/Users/garvey/Documents/Cline/MCP/genkit-mcp/index.js"
  ],
  "env": {},
  "disabled": false,
  "autoApprove": []
}
```

## Usage

### Starting the Server

```bash
cd /Users/garvey/Documents/Cline/MCP/genkit-mcp
node index.js
```

### Testing the Server

You can test the server using the included test script:

```bash
cd /Users/garvey/Documents/Cline/MCP/genkit-mcp
node test.js
```

Or use the MCP Inspector:

```bash
cd /Users/garvey/Documents/Cline/MCP/genkit-mcp
npx @modelcontextprotocol/inspector index.js
```

Then open http://localhost:5173 in your browser.

## Using with Cline

After configuring the MCP server in the Cline settings, you can use the tools and prompts in Cline by using the `use_mcp_tool` command:

```
<use_mcp_tool>
<server_name>github.com/firebase/genkit/tree/HEAD/js/plugins/mcp</server_name>
<tool_name>calculate</tool_name>
<arguments>
{
  "operation": "add",
  "a": 42,
  "b": 58
}
</arguments>
</use_mcp_tool>
```

Note: You may need to restart Cline after adding the server to the configuration.
