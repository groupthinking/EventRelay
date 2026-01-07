import json

config_path = "/Users/garvey/.gemini/antigravity/mcp_config.json"
try:
    with open(config_path, "r") as f:
        config = json.load(f)
    
    changed = False
    
    # Disable remote-github (Save 40 tools)
    if "mcpServers" in config and "remote-github" in config["mcpServers"]:
        if not config["mcpServers"]["remote-github"].get("disabled", False):
            config["mcpServers"]["remote-github"]["disabled"] = True
            print("Disabling 'remote-github' (Savings: ~40 tools)")
            changed = True
            
    # Ensure standard github is ENABLED
    if "mcpServers" in config and "github" in config["mcpServers"]:
        if config["mcpServers"]["github"].get("disabled", False):
             config["mcpServers"]["github"]["disabled"] = False
             print("Enabling standard 'github'")
             changed = True

    if changed:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print("Successfully updated mcp_config.json")
    else:
        print("No changes needed.")
        
except Exception as e:
    print(f"Error: {e}")
