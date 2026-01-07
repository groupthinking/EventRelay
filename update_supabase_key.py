import json

config_path = "/Users/garvey/.gemini/antigravity/mcp_config.json"
new_key = "sbp_b5d3df4f046a0cc1157371672b418a565320f8c7"

try:
    with open(config_path, "r") as f:
        config = json.load(f)
    
    if "mcpServers" in config and "supabase-mcp-server" in config["mcpServers"]:
        args = config["mcpServers"]["supabase-mcp-server"]["args"]
        # Find the index of --access-token and update the next element
        try:
            token_index = args.index("--access-token")
            if token_index + 1 < len(args):
                args[token_index + 1] = new_key
                print("Updated Supabase access token.")
                
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=2)
                print("Successfully saved mcp_config.json")
            else:
                print("Error: --access-token flag found but no value follows it.")
        except ValueError:
             print("Error: --access-token flag not found in args.")
    else:
        print("supabase-mcp-server not found in config")
except Exception as e:
    print(f"Error: {e}")
