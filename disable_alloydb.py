import json

config_path = "/Users/garvey/.gemini/antigravity/mcp_config.json"
try:
    with open(config_path, "r") as f:
        config = json.load(f)
    
    if "mcpServers" in config and "alloydb-postgres-admin" in config["mcpServers"]:
        config["mcpServers"]["alloydb-postgres-admin"]["disabled"] = True
        print("Disabling alloydb-postgres-admin...")
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print("Successfully updated mcp_config.json")
    else:
        print("alloydb-postgres-admin not found in config")
except Exception as e:
    print(f"Error: {e}")
