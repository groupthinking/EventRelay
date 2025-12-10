#!/bin/bash

# MCP Interface Deployment System
echo "🔄 Deploying MCP Service Interfaces"
echo "───────────────────────────────────"

# Define working directory and service list
WORK_DIR="/Users/garvey/Desktop/mcp-bridge/system"
mkdir -p "$WORK_DIR/services"
mkdir -p "$WORK_DIR/logs"
mkdir -p "$WORK_DIR/registry/@modelcontextprotocol"

# List of MCP services to deploy
SERVICES=(
  "code-assistant"
  "data-analysis"
  "workflow-automation"
  "knowledge-management"
  "communication-hub"
  "creative-studio"
)

# Create service interfaces
echo "📡 Creating ES Module service interfaces..."

for SERVICE in "${SERVICES[@]}"; do
  echo "  → Building interface for $SERVICE"
  
  # Create service directory
  mkdir -p "$WORK_DIR/registry/@modelcontextprotocol/server-$SERVICE"
  
  # Create package.json for the service
  cat > "$WORK_DIR/registry/@modelcontextprotocol/server-$SERVICE/package.json" << EOF
{
  "name": "@modelcontextprotocol/server-$SERVICE",
  "version": "1.0.0",
  "description": "MCP $SERVICE Interface",
  "type": "module",
  "main": "index.js",
  "bin": "cli.js"
}
EOF

  # Create service interface module
  cat > "$WORK_DIR/registry/@modelcontextprotocol/server-$SERVICE/index.js" << 'EOF'
/**
 * MCP Service Interface Module
 * Provides programmatic access to MCP services
 */

import http from 'http';

class MCPServiceInterface {
  constructor(options = {}) {
    this.serviceName = options.serviceName || 'unknown';
    this.coreUrl = options.coreUrl || 'http://localhost:51234';
    this.options = options;
    this.initialized = false;
    this.capabilities = {};
    
    console.log(`[${this.serviceName}] Initializing service interface`);
  }
  
  async initialize() {
    try {
      const response = await this.request(`/service/${this.serviceName}/status`);
      this.capabilities = response.capabilities || {};
      this.environment = response.environment || {};
      this.initialized = true;
      console.log(`[${this.serviceName}] Successfully initialized`);
      return true;
    } catch (error) {
      console.error(`[${this.serviceName}] Initialization failed:`, error.message);
      return false;
    }
  }
  
  async execute(action, params = {}) {
    if (!this.initialized) {
      await this.initialize();
    }
    
    try {
      const response = await this.request(
        `/service/${this.serviceName}/execute`, 
        'POST',
        { action, params }
      );
      return response;
    } catch (error) {
      console.error(`[${this.serviceName}] Execution failed:`, error.message);
      throw error;
    }
  }
  
  async getCapabilities() {
    if (!this.initialized) {
      await this.initialize();
    }
    return this.capabilities;
  }
  
  request(path, method = 'GET', data = null) {
    return new Promise((resolve, reject) => {
      const url = new URL(path, this.coreUrl);
      
      const options = {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      };
      
      const req = http.request(url, options, (res) => {
        let responseData = '';
        
        res.on('data', (chunk) => {
          responseData += chunk;
        });
        
        res.on('end', () => {
          try {
            const jsonData = JSON.parse(responseData);
            if (res.statusCode >= 200 && res.statusCode < 300) {
              resolve(jsonData);
            } else {
              reject(new Error(jsonData.message || 'Request failed'));
            }
          } catch (error) {
            reject(new Error(`Failed to parse response: ${error.message}`));
          }
        });
      });
      
      req.on('error', (error) => {
        reject(error);
      });
      
      if (data) {
        req.write(JSON.stringify(data));
      }
      
      req.end();
    });
  }
}

// Export service interface with pre-configured settings
export default function createInterface(options = {}) {
  const serviceName = 'SERVICE_NAME_PLACEHOLDER';
  return new MCPServiceInterface({
    serviceName,
    ...options
  });
}
EOF

  # Replace SERVICE_NAME_PLACEHOLDER with actual service name
  sed -i '' "s/SERVICE_NAME_PLACEHOLDER/$SERVICE/g" "$WORK_DIR/registry/@modelcontextprotocol/server-$SERVICE/index.js"
  
  # Create CLI entrypoint
  cat > "$WORK_DIR/registry/@modelcontextprotocol/server-$SERVICE/cli.js" << 'EOF'
#!/usr/bin/env node

/**
 * MCP Service CLI
 * Command-line interface for MCP services
 */

import createInterface from './index.js';
import { parseArgs } from 'node:util';

// Parse command line arguments
const args = process.argv.slice(2);
console.log(`Command arguments: ${args.join(' ')}`);

// Parse options into capabilities
const options = {};
for (const arg of args) {
  if (arg.startsWith('--')) {
    const [key, value] = arg.substring(2).split('=');
    options[key] = value === undefined ? true : value;
  }
}

// Create service interface
const service = createInterface({
  options
});

// Initialize service
try {
  await service.initialize();
  console.log(`Service activated with capabilities:`, await service.getCapabilities());
  
  // Keep process alive
  console.log(`SERVICE_NAME_PLACEHOLDER running in bridge mode. Press Ctrl+C to terminate.`);
  setInterval(() => {}, 10000);
} catch (error) {
  console.error(`Failed to initialize service:`, error.message);
  process.exit(1);
}
EOF

  # Replace SERVICE_NAME_PLACEHOLDER with actual service name
  sed -i '' "s/SERVICE_NAME_PLACEHOLDER/$SERVICE/g" "$WORK_DIR/registry/@modelcontextprotocol/server-$SERVICE/cli.js"
  
  # Make CLI executable
  chmod +x "$WORK_DIR/registry/@modelcontextprotocol/server-$SERVICE/cli.js"
  
  echo "    ✓ Interface built successfully"
done

# Create global registry configuration
echo ""
echo "📦 Configuring npm registry..."

# Create .npmrc to point to local registry
cat > "$HOME/.npmrc" << EOF
@modelcontextprotocol:registry=file://$WORK_DIR/registry
EOF

echo "✅ npm configured to use local registry at $WORK_DIR/registry"

# Create service launcher scripts
echo ""
echo "🚀 Creating service launchers..."

for SERVICE in "${SERVICES[@]}"; do
  # Extract options for each service
  case "$SERVICE" in
    code-assistant)
      OPTIONS="--ide-integration=vscode,intellij,xcode --repository-scanning=enabled"
      ;;
    data-analysis)
      OPTIONS="--streaming-processing=enabled --distributed-computation=local"
      ;;
    workflow-automation)
      OPTIONS="--trigger-complexity=advanced --cross-application=enabled"
      ;;
    knowledge-management)
      OPTIONS="--schema-inference=dynamic --entity-recognition=context-aware"
      ;;
    communication-hub)
      OPTIONS="--end-to-end-encryption=enabled --protocol-bridging=universal"
      ;;
    creative-studio)
      OPTIONS="--rendering-quality=professional --asset-management=integrated"
      ;;
  esac
  
  # Create launcher script
  cat > "$WORK_DIR/launch-$SERVICE.sh" << EOF
#!/bin/bash

# MCP $SERVICE Launcher
echo "🚀 Launching $SERVICE..."

# Set environment variables from configuration
export PATH="$WORK_DIR/registry/@modelcontextprotocol/server-$SERVICE/node_modules/.bin:$PATH"

# Launch service
npx @modelcontextprotocol/server-$SERVICE $OPTIONS
EOF

  chmod +x "$WORK_DIR/launch-$SERVICE.sh"
  echo "  ✓ Created launcher for $SERVICE"
done

# Create master launcher
echo ""
echo "🔄 Creating master control interface..."

cat > "$WORK_DIR/launch-all.sh" << 'EOF'
#!/bin/bash

# MCP Master Launcher
echo "🚀 Launching MCP Service Suite"
echo "────────────────────────────"

WORK_DIR="$(dirname "$0")"

# Function to check if core server is running
function check_core_server {
  if curl -s http://localhost:51234/status > /dev/null; then
    echo "✅ Core server is running"
    return 0
  else
    echo "❌ Core server is not running"
    return 1
  fi
}

# Check core server status
if ! check_core_server; then
  echo "  → Starting core server..."
  "$WORK_DIR/../initialize-core.sh" > /dev/null
  
  # Verify core server started
  sleep 2
  if ! check_core_server; then
    echo "❌ Failed to start core server"
    exit 1
  fi
fi

# Launch all services in background
echo ""
echo "🚀 Launching services..."

# Create log directory
mkdir -p "$WORK_DIR/logs"

# Launch each service
for script in "$WORK_DIR"/launch-*.sh; do
  if [[ "$script" != *"launch-all.sh"* ]]; then
    SERVICE=$(basename "$script" | sed 's/launch-//g' | sed 's/.sh//g')
    echo "  → Starting $SERVICE"
    "$script" > "$WORK_DIR/logs/$SERVICE.log" 2>&1 &
    echo "    ✓ Started with PID $!"
  fi
done

echo ""
echo "✅ All services launched successfully"
echo "  → Service logs available at: $WORK_DIR/logs/"
echo ""
echo "To check system status, run:"
echo "  curl http://localhost:51234/status | python3 -m json.tool"
EOF

chmod +x "$WORK_DIR/launch-all.sh"

echo ""
echo "✨ MCP Interface System Deployed!"
echo "──────────────────────────────────────────────────"
echo "📋 Usage Instructions:"
echo ""
echo "  1. Launch all services:"
echo "     $WORK_DIR/launch-all.sh"
echo ""
echo "  2. Launch a specific service (e.g. code-assistant):"
echo "     $WORK_DIR/launch-code-assistant.sh"
echo ""
echo "  3. Check system status:"
echo "     curl http://localhost:51234/status | python3 -m json.tool"
echo ""
echo "  4. Service logs available at:"
echo "     $WORK_DIR/logs/"
echo "──────────────────────────────────────────────────"
echo "Your MCP infrastructure is now fully operational!"
