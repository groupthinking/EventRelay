import json

config_path = "/Users/garvey/.gemini/antigravity/mcp_config.json"
# New Access Token (Main Master)
new_key = "sbp_19773a3a528e4b460354963ac80510d9d979dbdb"

try:
    with open(config_path, "r") as f:
        config = json.load(f)
    
    # 1. Update the Access Token for the existing npm-based server
    if "mcpServers" in config and "supabase-mcp-server" in config["mcpServers"]:
        args = config["mcpServers"]["supabase-mcp-server"]["args"]
        try:
            token_index = args.index("--access-token")
            if token_index + 1 < len(args):
                args[token_index + 1] = new_key
                print("Updated 'supabase-mcp-server' (npm) access token.")
        except ValueError:
             print("Error: --access-token flag not found in args.")
    
    # 2. Add the HTTP/SSE based server entry if requested (Currently user provided HTTP generic config)
    # The config format provided by user '{"servers": ...}' looks like a different MCP client config (e.g. Claude Desktop).
    # Since we are using 'mcp_config.json' which uses 'mcpServers' object, we will stick to the NPM server for now 
    # BUT update it with the new key which seems to be the main actionable item for the 'antigravity' agent context.
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print("Successfully saved mcp_config.json")

except Exception as e:
    print(f"Error: {e}")
