# Setting Up Model Context Protocol (MCP) Servers for Cline

This guide summarizes the process of setting up and integrating the Operative.sh web-eval-agent MCP server with Cline.

## Overview of the MCP System

The Model Context Protocol (MCP) allows AI assistants like Cline to extend their capabilities by connecting to external services through a standardized interface. These services can provide:

- Tools that perform specific actions (like evaluating a web page)
- Resources that provide information (like API responses or system data)

## Web Evaluation Agent Setup

We set up the web-eval-agent from Operative.sh, which provides tools for:

- Navigating and testing web applications
- Capturing network traffic
- Collecting console errors
- Performing autonomous debugging

## Installation Steps

1. **Clone the Repository**
   ```bash
   mkdir -p ~/Documents/Cline/MCP/web-eval-agent
   cd ~/Documents/Cline/MCP/web-eval-agent
   git clone https://github.com/Operative-Sh/web-eval-agent.git .
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

3. **Create MCP Configuration**
   The MCP server configuration is stored in:  
   `~/Library/Application Support/Cline/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

   Structure:
   ```json
   {
     "mcpServers": {
       "github.com/Operative-Sh/web-eval-agent": {
         "command": "python",
         "args": ["-m", "webEvalAgent.mcp_server"],
         "cwd": "/Users/garvey/Documents/Cline/MCP/web-eval-agent",
         "env": {
           "OPERATIVE_API_KEY": "your-api-key"
         },
         "disabled": false,
         "autoApprove": []
       }
     }
   }
   ```

4. **Obtaining API Keys**
   For the web-eval-agent, an API key from Operative.sh is required. Visit their website and create an account to get an API key.

5. **Simplified Alternative**
   We also created a simplified version of the web evaluation server:
   - `simple_mcp_server.py` - A simplified MCP server that provides basic web evaluation functionality without requiring external API keys

## Testing with a Local Web Page

To test the web evaluation agent, we:

1. Created a test HTML page with various UI elements and forms
2. Set up a simple HTTP server to serve the page locally
3. Attempted to use the MCP tool to evaluate the page

## Troubleshooting

Common issues when setting up MCP servers:

1. **API Key Issues**
   - Invalid or missing API keys
   - Environment variable not properly passed to the MCP server process

2. **Connection Problems**
   - MCP server not starting properly
   - Path configuration issues in the settings file
   - Permissions issues with executing the server files

3. **Restart Requirements**
   - Cline may need to be restarted to pick up new MCP server configurations

## Best Practices

1. Keep API keys secure and don't commit them to version control
2. Use clear and descriptive server names in the MCP settings
3. Test MCP tools with simple examples before using them in complex tasks
4. Check server logs for error messages when troubleshooting

## Additional Resources

1. MCP Documentation: Available through the `load_mcp_documentation` tool in Cline
2. Operative.sh Web Eval Agent: https://github.com/Operative-Sh/web-eval-agent
3. Model Context Protocol: Part of the Claude ecosystem for extending AI assistant capabilities
