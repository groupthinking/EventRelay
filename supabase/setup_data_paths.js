/**
 * Data Path Setup and Validation Script
 * 
 * This script sets up and validates the configured data management paths
 */

const fs = require('fs');
const path = require('path');
const { DATA_PATHS, MCP } = require('./lib/config');

function setupDataPaths() {
  console.log('🏗️  Setting up MCP data management structure...');
  
  const requiredPaths = [
    { path: DATA_PATHS.MCP_DATA, name: 'Primary MCP Data Storage' },
    { path: DATA_PATHS.CONVERSATIONS, name: 'Conversations Storage' },
    { path: DATA_PATHS.PROMPTS, name: 'Generated Prompts Storage' }
  ];
  
  // Create required directories
  for (const { path: dirPath, name } of requiredPaths) {
    try {
      if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
        console.log(`✅ Created: ${name} at ${dirPath}`);
      } else {
        console.log(`✅ Exists: ${name} at ${dirPath}`);
      }
    } catch (error) {
      console.error(`❌ Failed to create ${name}: ${error.message}`);
    }
  }
  
  // Validate optional paths
  const optionalPaths = [
    { path: DATA_PATHS.META_RUNTIME, name: 'Meta State Runtime Pack' },
    { path: DATA_PATHS.PROJECT_ROOT, name: 'Project Root' }
  ];
  
  for (const { path: dirPath, name } of optionalPaths) {
    if (fs.existsSync(dirPath)) {
      console.log(`✅ Found: ${name} at ${dirPath}`);
    } else {
      console.log(`⚠️  Not found: ${name} at ${dirPath}`);
    }
  }
  
  // Create initial data files
  const dataFiles = [
    {
      path: path.join(DATA_PATHS.MCP_DATA, 'projects.json'),
      content: '[]',
      name: 'Projects Database'
    },
    {
      path: path.join(DATA_PATHS.MCP_DATA, 'mcp_contexts.json'),
      content: '[]',
      name: 'MCP Contexts Database'
    },
    {
      path: path.join(DATA_PATHS.CONVERSATIONS, 'index.json'),
      content: '{"conversations": [], "last_updated": "' + new Date().toISOString() + '"}',
      name: 'Conversations Index'
    },
    {
      path: path.join(DATA_PATHS.PROMPTS, 'index.json'),
      content: '{"prompts": [], "last_updated": "' + new Date().toISOString() + '"}',
      name: 'Prompts Index'
    }
  ];
  
  for (const { path: filePath, content, name } of dataFiles) {
    try {
      if (!fs.existsSync(filePath)) {
        fs.writeFileSync(filePath, content, 'utf8');
        console.log(`✅ Created: ${name} at ${filePath}`);
      } else {
        console.log(`✅ Exists: ${name} at ${filePath}`);
      }
    } catch (error) {
      console.error(`❌ Failed to create ${name}: ${error.message}`);
    }
  }
  
  console.log('\n📊 Data Management Configuration:');
  console.log(`- Primary Storage: ${DATA_PATHS.MCP_DATA}`);
  console.log(`- Conversations: ${DATA_PATHS.CONVERSATIONS}`);
  console.log(`- Prompts: ${DATA_PATHS.PROMPTS}`);
  console.log(`- Meta Runtime: ${DATA_PATHS.META_RUNTIME}`);
  console.log(`- Project Root: ${DATA_PATHS.PROJECT_ROOT}`);
  
  console.log('\n🎉 Data path setup complete!');
  return true;
}

// Scan and report on existing data
function scanExistingData() {
  console.log('\n🔍 Scanning for existing data...');
  
  const scanResults = {};
  
  // Scan each configured path
  Object.entries(DATA_PATHS).forEach(([key, dirPath]) => {
    scanResults[key] = {
      path: dirPath,
      exists: fs.existsSync(dirPath),
      files: []
    };
    
    if (scanResults[key].exists) {
      try {
        const files = fs.readdirSync(dirPath, { recursive: true });
        scanResults[key].files = files.slice(0, 10); // Limit to first 10 files
        scanResults[key].totalFiles = files.length;
      } catch (error) {
        scanResults[key].error = error.message;
      }
    }
  });
  
  // Report findings
  Object.entries(scanResults).forEach(([key, result]) => {
    if (result.exists) {
      console.log(`📁 ${key}: ${result.totalFiles || 0} files in ${result.path}`);
      if (result.files.length > 0) {
        console.log(`   Sample files: ${result.files.slice(0, 3).join(', ')}${result.totalFiles > 3 ? '...' : ''}`);
      }
    } else {
      console.log(`📁 ${key}: Not found at ${result.path}`);
    }
  });
  
  return scanResults;
}

// Run setup if called directly
if (require.main === module) {
  setupDataPaths();
  scanExistingData();
}

module.exports = { setupDataPaths, scanExistingData };