import json

config_path = "/Users/garvey/.gemini/antigravity/mcp_config.json"
new_url = "https://mcp.supabase.com/mcp?project_ref=stutwuhyjnhtasukqxzg&features=docs%2Caccount%2Cdatabase%2Cdebugging%2Cdevelopment%2Cfunctions%2Cbranching%2Cstorage"

try:
    with open(config_path, "r") as f:
        config = json.load(f)
    
    # Remove the npm-based server if it exists
    if "mcpServers" in config:
        if "supabase-mcp-server" in config["mcpServers"]:
            del config["mcpServers"]["supabase-mcp-server"]
            print("Removed local 'supabase-mcp-server'.")

        # Add the new HTTP/SSE based server
        config["mcpServers"]["supabase"] = {
            "url": new_url,
            "headers": {
                # We need to ensure authentication is passed if required by the remote MCP.
                # The prompt implied the key 'sbp_19773a3a528e4b460354963ac80510d9d979dbdb' 
                # might be needed here or the URL handles it (project_ref is in URL).
                # Usually remote MCPs need an auth header if they aren't public.
                # I'll check if the previous token is relevant.
            }
            # Note: The user snippet showed "type": "http", but usually "url" is sufficient for SSE clients.
            # I will include "type": "sse" if the client supports strict typing, 
            # but standard is often just 'url' or 'command'.
        }
        
        # We might need to inject the Authorization header with the sbp_ token 
        # because the project is private?
        # The user provided 'sbp_19773a3a528e4b460354963ac80510d9d979dbdb'.
        config["mcpServers"]["supabase"]["headers"] = {
             "Authorization": "Bearer sbp_19773a3a528e4b460354963ac80510d9d979dbdb" 
        }

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print("Successfully updated mcp_config.json to use Supabase Remote MCP.")

except Exception as e:
    print(f"Error: {e}")
