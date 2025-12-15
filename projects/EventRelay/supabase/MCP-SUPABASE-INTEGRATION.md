# Supabase MCP Integration Guide

This guide explains how to integrate the Model Context Protocol (MCP) Framework with Supabase using the official Supabase MCP server. This integration allows AI tools to interact directly with your Supabase projects.

## Overview

The Supabase MCP server acts as a bridge between AI tools (like Cursor, VS Code, Claude) and your Supabase projects. When properly configured, your AI tools can:

- Query your Supabase database
- Manage Supabase projects
- Access Supabase functions and APIs
- Perform database operations based on natural language requests

## Setup Process

### 1. Create a Supabase Personal Access Token (PAT)

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Navigate to your account settings (click on your profile icon)
3. Go to the "Access Tokens" section
4. Create a new token named "MCP Integration"
5. Copy the generated token (you'll need it for configuration)

### 2. Run the Setup Script

The easiest way to configure MCP is to run the included setup script:

```bash
./setup_supabase_mcp.sh
```

This script will:
- Create necessary configuration directories and files
- Guide you through the setup process
- Provide troubleshooting tips

### 3. Configure MCP Files Manually (Alternative)

If you prefer to set up manually, you'll need to create the following files:

#### For Cursor:

Create `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@supabase/mcp-server-supabase@latest",
        "--access-token",
        "YOUR_SUPABASE_ACCESS_TOKEN"
      ]
    }
  }
}
```

Replace `YOUR_SUPABASE_ACCESS_TOKEN` with your actual token.

#### For VS Code (Copilot):

Create `.vscode/mcp.json`:

```json
{
  "inputs": [
    {
      "type": "promptString",
      "id": "supabase-access-token",
      "description": "Supabase personal access token",
      "password": true
    }
  ],
  "servers": {
    "supabase": {
      "command": "npx",
      "args": ["-y", "@supabase/mcp-server-supabase@latest"],
      "env": {
        "SUPABASE_ACCESS_TOKEN": "${input:supabase-access-token}"
      }
    }
  }
}
```

#### For Claude and other tools:

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@supabase/mcp-server-supabase@latest",
        "--access-token",
        "YOUR_SUPABASE_ACCESS_TOKEN"
      ]
    }
  }
}
```

Replace `YOUR_SUPABASE_ACCESS_TOKEN` with your actual token.

### 4. Verify Configuration

To test if your configuration is correct, you can run:

   ```bash
node test_supabase_mcp_connection.js
```

## Using MCP with AI Tools

### Cursor

1. Open Cursor
2. Navigate to Settings > MCP
3. You should see a green active status for the Supabase MCP server
4. You can now ask the AI about your Supabase projects and resources

### VS Code with Copilot

1. Open VS Code
2. Open Copilot chat (Ctrl+Shift+I or Cmd+Shift+I)
3. Switch to "Agent" mode
4. The first time you use MCP features, you'll be prompted for your Supabase token
5. You can now ask Copilot about your Supabase projects

### Claude

1. Open Claude desktop
2. You should see a hammer (MCP) icon that indicates MCP tools are available
3. You can now ask Claude about your Supabase projects

## Local Supabase Integration

If you're using a local Supabase instance, you can connect to it using the Postgres MCP server:

1. Get your database connection string by running:
   ```bash
   supabase status
   ```
   
2. Copy the DB URL field from the output

3. Update your MCP configuration to use the Postgres server:
   ```json
   {
     "mcpServers": {
       "supabase": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-postgres", "YOUR_CONNECTION_STRING"]
       }
     }
   }
   ```

Replace `YOUR_CONNECTION_STRING` with the actual connection string.

## Example Queries

Once connected, you can ask your AI tools:

- "What projects do I have in my Supabase account?"
- "Create a new table called users with name, email and profile_picture columns"
- "Show me the schema of the products table"
- "Query all active users who signed up in the last month"
- "Check if my database has any tables without primary keys"

## Troubleshooting

If you encounter issues with the MCP connection:

1. **Check your access token**: Make sure your Supabase personal access token is valid and has the necessary permissions
2. **Verify configuration files**: Ensure your MCP configuration files are correctly formatted
3. **Restart your IDE/AI tool**: Some tools require a restart to detect MCP configuration changes
4. **Check logs**: Look for any error messages in the console output
5. **Update packages**: Run `npm install -g @supabase/mcp-server-supabase@latest` to ensure you have the latest version

## Manual .env File Creation

If you are unable to create `.env.local` in `mcp-supabase-frontend/` or `~/.config/supabase-mcp/.env` automatically, please create them manually as described in the README troubleshooting section.

Each file should contain:

```
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
MCP_ACCESS_TOKEN=your_mcp_access_token
```

These variables are required for MCP-Supabase integration. If you do not have your Supabase credentials or MCP access token, follow the setup instructions above or contact your system administrator.

## Reference

For more information, see:
- [Supabase MCP Documentation](https://supabase.com/docs/guides/getting-started/mcp)
- [Model Context Protocol (MCP) Specification](https://modelcontextprotocol.org)
- [Supabase API Documentation](https://supabase.com/docs/reference) 