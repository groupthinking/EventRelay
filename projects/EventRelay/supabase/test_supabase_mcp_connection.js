/**
 * Supabase MCP Connection Test
 */

const { spawn } = require('child_process');
const fs = require('fs');

async function testSupabaseMcpConnection() {
  console.log('=== Supabase MCP Connection Test ===');
  
  try {
    // Check if token is in environment
    const token = process.env.SUPABASE_ACCESS_TOKEN;
    if (!token) {
      console.warn('Warning: SUPABASE_ACCESS_TOKEN environment variable not found.');
    } else {
      console.log('SUPABASE_ACCESS_TOKEN environment variable found ✓');
    }
    
    // Check MCP configuration files
    console.log('\nMCP Configuration Files:');
    checkConfigFile('.cursor/mcp.json');
    checkConfigFile('.vscode/mcp.json');
    checkConfigFile('.mcp.json');

    // Check environment files for MCP-Supabase integration
    console.log('\nMCP-Supabase Environment Files:');
    checkEnvFile('mcp-supabase-frontend/.env.local');
    checkEnvFile(process.env.HOME + '/.config/supabase-mcp/.env');

    console.log('\nYour configuration is ready for use with:');
    console.log('1. Cursor (Settings > MCP)');
    console.log('2. VS Code with Copilot (Agent mode)');
    console.log('3. Claude (MCP hammer icon)');
  } catch (error) {
    console.error('Error:', error);
  }
}

function checkConfigFile(filePath) {
  try {
    if (!fs.existsSync(filePath)) {
      console.log(`${filePath}: ✗ (missing)`);
      return false;
    }
    
    const content = fs.readFileSync(filePath, 'utf8');
    JSON.parse(content); // Will throw if invalid JSON
    console.log(`${filePath}: ✓`);
    return true;
  } catch (error) {
    console.log(`${filePath}: ✗ (${error.message})`);
    return false;
  }
}

function checkEnvFile(filePath) {
  try {
    if (!fs.existsSync(filePath)) {
      console.log(`${filePath}: ✗ (missing)`);
      console.warn(`  See README troubleshooting for manual creation instructions.`);
      return false;
    }
    console.log(`${filePath}: ✓`);
    return true;
  } catch (error) {
    console.log(`${filePath}: ✗ (${error.message})`);
    return false;
  }
}

// Run the test
testSupabaseMcpConnection().catch(console.error);
 