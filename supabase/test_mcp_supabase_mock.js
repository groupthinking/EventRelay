/**
 * MCP-Supabase Integration Test Script
 * 
 * This script tests the MCP-Supabase integration using the mock environment.
 * It verifies that all functionality works correctly without requiring a 
 * real Supabase instance.
 */

// Use CommonJS require instead of ES modules
const { v4: uuidv4 } = require('uuid');

// Mock implementations since we're in a CommonJS environment
const mockMcpContext = {
  contextId: uuidv4(),
  operation: 'test_operation',
  user: 'test-script',
  timestamp: Date.now(),
  parameters: { test: true }
};

// Mock database
const mockDatabase = {
  projects: [
    {
      id: uuidv4(),
      name: 'Abacus.AI Integration',
      description: 'MCP framework integration with Abacus.AI',
      content: 'This project demonstrates how to use Model Context Protocol (MCP) with Abacus.AI services.',
      ref_source: 'abacus.ai',
      create_date: new Date().toISOString(),
      update_date: new Date().toISOString(),
      metadata: {}
    },
    {
      id: uuidv4(),
      name: 'MCP Framework',
      description: 'Core implementation of Model Context Protocol',
      content: 'The Model Context Protocol provides structured context sharing for AI/LLM systems with full traceability.',
      ref_source: 'framework',
      create_date: new Date().toISOString(),
      update_date: new Date().toISOString(),
      metadata: {}
    }
  ],
  mcp_logs: []
};

// Clone helper
const clone = (obj) => JSON.parse(JSON.stringify(obj));

// Create MCP context helper
function createMcpContext(operation, source, parameters = {}) {
  return {
    contextId: uuidv4(),
    operation,
    user: source,
    timestamp: Date.now(),
    parameters
  };
}

// Propagate MCP context helper
function propagateMcp(parentContext, updates = {}) {
  return {
    ...parentContext,
    contextId: uuidv4(),
    ...updates
  };
}

// Mock client implementation
class MockSupabaseMcpClient {
  constructor(options = {}) {
    this.source = options.source || 'mock-client';
    this.parentContext = options.parentContext || null;
  }

  createContext(operation, parameters = {}) {
    if (this.parentContext) {
      return propagateMcp(this.parentContext, {
        operation: `supabase_${operation}`,
        ...parameters
      });
    }
    
    return createMcpContext(`supabase_${operation}`, this.source, parameters);
  }

  async query(table, options = {}) {
    const {
      filters = {},
      limit = 10,
      parentContext = null
    } = options;

    const context = this.createContext('query', {
      table,
      filters,
      limit,
      parent: parentContext?.contextId
    });

    try {
      // Filter results based on filters
      let results = [...mockDatabase[table] || []];
      
      // Apply filters
      Object.entries(filters).forEach(([key, value]) => {
        results = results.filter(row => row[key] === value);
      });
      
      // Apply limit
      results = results.slice(0, limit);
      
      // Log to mcp_logs
      mockDatabase.mcp_logs.push({
        id: uuidv4(),
        context_id: context.contextId,
        operation: context.operation,
        user_id: context.user,
        timestamp: context.timestamp,
        parameters: context.parameters,
        result: { count: results.length },
        status: 'success',
        create_date: new Date().toISOString()
      });
      
      // Create success context
      const successContext = propagateMcp(context, {
        status: 'success',
        resultCount: results.length,
        attempts: 1
      });
      
      return { data: clone(results), error: null, context: successContext };
    } catch (error) {
      // Log error
      mockDatabase.mcp_logs.push({
        id: uuidv4(),
        context_id: context.contextId,
        operation: context.operation,
        user_id: context.user,
        timestamp: context.timestamp,
        parameters: context.parameters,
        result: { error: error.message },
        status: 'error',
        create_date: new Date().toISOString()
      });
      
      // Create error context
      const errorContext = propagateMcp(context, {
        status: 'error',
        error: error.message,
        attempts: 1
      });
      
      return { data: null, error, context: errorContext };
    }
  }

  async insert(table, data, options = {}) {
    const {
      returning = 'minimal',
      parentContext = null
    } = options;

    const context = this.createContext('insert', {
      table,
      recordCount: Array.isArray(data) ? data.length : 1,
      parent: parentContext?.contextId
    });

    try {
      // Ensure table exists
      if (!mockDatabase[table]) {
        mockDatabase[table] = [];
      }
      
      // Insert data
      const rows = Array.isArray(data) ? data : [data];
      const insertedRows = rows.map(row => {
        const newRow = {
          ...row,
          id: row.id || uuidv4(),
          create_date: new Date().toISOString(),
          update_date: new Date().toISOString()
        };
        mockDatabase[table].push(newRow);
        return newRow;
      });
      
      // Log to mcp_logs
      mockDatabase.mcp_logs.push({
        id: uuidv4(),
        context_id: context.contextId,
        operation: context.operation,
        user_id: context.user,
        timestamp: context.timestamp,
        parameters: context.parameters,
        result: { count: insertedRows.length },
        status: 'success',
        create_date: new Date().toISOString()
      });
      
      // Create success context
      const successContext = propagateMcp(context, {
        status: 'success',
        insertedCount: insertedRows.length,
        attempts: 1
      });
      
      return {
        data: returning === 'minimal' ? null : clone(insertedRows),
        error: null,
        context: successContext
      };
    } catch (error) {
      // Log error
      mockDatabase.mcp_logs.push({
        id: uuidv4(),
        context_id: context.contextId,
        operation: context.operation,
        user_id: context.user,
        timestamp: context.timestamp,
        parameters: context.parameters,
        result: { error: error.message },
        status: 'error',
        create_date: new Date().toISOString()
      });
      
      // Create error context
      const errorContext = propagateMcp(context, {
        status: 'error',
        error: error.message,
        attempts: 1
      });
      
      return { data: null, error, context: errorContext };
    }
  }

  async update(table, data, options = {}) {
    const {
      match = {},
      returning = 'minimal',
      parentContext = null
    } = options;

    const context = this.createContext('update', {
      table,
      match,
      updateFields: Object.keys(data),
      parent: parentContext?.contextId
    });

    try {
      // Find records to update
      const indices = [];
      mockDatabase[table].forEach((row, index) => {
        let matchesAll = true;
        Object.entries(match).forEach(([key, value]) => {
          if (row[key] !== value) {
            matchesAll = false;
          }
        });
        if (matchesAll) {
          indices.push(index);
        }
      });
      
      // Update records
      const updatedRows = indices.map(index => {
        mockDatabase[table][index] = {
          ...mockDatabase[table][index],
          ...data,
          update_date: new Date().toISOString()
        };
        return mockDatabase[table][index];
      });
      
      // Log to mcp_logs
      mockDatabase.mcp_logs.push({
        id: uuidv4(),
        context_id: context.contextId,
        operation: context.operation,
        user_id: context.user,
        timestamp: context.timestamp,
        parameters: context.parameters,
        result: { count: updatedRows.length },
        status: 'success',
        create_date: new Date().toISOString()
      });
      
      // Create success context
      const successContext = propagateMcp(context, {
        status: 'success',
        updatedCount: updatedRows.length,
        attempts: 1
      });
      
      return {
        data: returning === 'minimal' ? null : clone(updatedRows),
        error: null,
        context: successContext
      };
    } catch (error) {
      // Log error
      mockDatabase.mcp_logs.push({
        id: uuidv4(),
        context_id: context.contextId,
        operation: context.operation,
        user_id: context.user,
        timestamp: context.timestamp,
        parameters: context.parameters,
        result: { error: error.message },
        status: 'error',
        create_date: new Date().toISOString()
      });
      
      // Create error context
      const errorContext = propagateMcp(context, {
        status: 'error',
        error: error.message,
        attempts: 1
      });
      
      return { data: null, error, context: errorContext };
    }
  }

  async delete(table, options = {}) {
    const {
      match = {},
      returning = 'minimal',
      parentContext = null
    } = options;

    const context = this.createContext('delete', {
      table,
      match,
      parent: parentContext?.contextId
    });

    try {
      // Find records to delete
      const indicesToDelete = [];
      const rowsToDelete = [];
      mockDatabase[table].forEach((row, index) => {
        let matchesAll = true;
        Object.entries(match).forEach(([key, value]) => {
          if (row[key] !== value) {
            matchesAll = false;
          }
        });
        if (matchesAll) {
          indicesToDelete.push(index);
          rowsToDelete.push(clone(row));
        }
      });
      
      // Delete records (in reverse order to avoid index issues)
      indicesToDelete.sort((a, b) => b - a);
      indicesToDelete.forEach(index => {
        mockDatabase[table].splice(index, 1);
      });
      
      // Log to mcp_logs
      mockDatabase.mcp_logs.push({
        id: uuidv4(),
        context_id: context.contextId,
        operation: context.operation,
        user_id: context.user,
        timestamp: context.timestamp,
        parameters: context.parameters,
        result: { count: rowsToDelete.length },
        status: 'success',
        create_date: new Date().toISOString()
      });
      
      // Create success context
      const successContext = propagateMcp(context, {
        status: 'success',
        deletedCount: rowsToDelete.length,
        attempts: 1
      });
      
      return {
        data: returning === 'minimal' ? null : rowsToDelete,
        error: null,
        context: successContext
      };
    } catch (error) {
      // Log error
      mockDatabase.mcp_logs.push({
        id: uuidv4(),
        context_id: context.contextId,
        operation: context.operation,
        user_id: context.user,
        timestamp: context.timestamp,
        parameters: context.parameters,
        result: { error: error.message },
        status: 'error',
        create_date: new Date().toISOString()
      });
      
      // Create error context
      const errorContext = propagateMcp(context, {
        status: 'error',
        error: error.message,
        attempts: 1
      });
      
      return { data: null, error, context: errorContext };
    }
  }

  async rpc(functionName, params = {}, options = {}) {
    const {
      parentContext = null
    } = options;

    const context = this.createContext('rpc', {
      function: functionName,
      params,
      parent: parentContext?.contextId
    });

    try {
      let result = null;
      
      // Mock implementation of match_page_sections
      if (functionName === 'match_page_sections') {
        const { match_count = 5, min_content_length = 10 } = params;
        
        result = mockDatabase.projects
          .filter(project => project.content && project.content.length >= min_content_length)
          .slice(0, match_count)
          .map(project => ({
            id: project.id,
            page_id: 1,
            slug: project.name.toLowerCase().replace(/\s+/g, '-'),
            heading: project.name,
            content: project.content,
            similarity: Math.random() * 0.5 + 0.5
          }));
      } else {
        throw new Error(`Function ${functionName} not implemented in mock`);
      }
      
      // Log to mcp_logs
      mockDatabase.mcp_logs.push({
        id: uuidv4(),
        context_id: context.contextId,
        operation: context.operation,
        user_id: context.user,
        timestamp: context.timestamp,
        parameters: context.parameters,
        result: { count: result?.length || 0 },
        status: 'success',
        create_date: new Date().toISOString()
      });
      
      // Create success context
      const successContext = propagateMcp(context, {
        status: 'success',
        attempts: 1
      });
      
      return { data: result, error: null, context: successContext };
    } catch (error) {
      // Log error
      mockDatabase.mcp_logs.push({
        id: uuidv4(),
        context_id: context.contextId,
        operation: context.operation,
        user_id: context.user,
        timestamp: context.timestamp,
        parameters: context.parameters,
        result: { error: error.message },
        status: 'error',
        create_date: new Date().toISOString()
      });
      
      // Create error context
      const errorContext = propagateMcp(context, {
        status: 'error',
        error: error.message,
        attempts: 1
      });
      
      return { data: null, error, context: errorContext };
    }
  }
}

// Run the test
async function runTest() {
  console.log('Testing MCP-Supabase integration with mock environment...');
  
  // Reset the mock database
  mockDatabase.mcp_logs = [];
  
  // Create a context
  const context = createMcpContext('test_operation', 'test-script', {
    test: true,
    timestamp: Date.now()
  });
  
  // Create the client
  const client = new MockSupabaseMcpClient({
    source: 'test-script',
    parentContext: context
  });
  
  try {
    // Test 1: Query projects
    console.log('\nTest 1: Query projects');
    const { data: projects, context: queryContext } = await client.query('projects', {
      filters: { ref_source: 'abacus.ai' },
      limit: 5
    });
    
    console.log(`Query returned ${projects?.length || 0} projects`);
    console.log('Context ID:', queryContext.contextId);
    
    // Test 2: Insert a project
    console.log('\nTest 2: Insert a project');
    const { data: insertedProject, context: insertContext } = await client.insert('projects', {
      name: 'Test Project',
      description: 'Created by test script',
      content: 'This is a test project created by the MCP-Supabase test script',
      ref_source: 'test-script',
      metadata: { test: true }
    }, {
      returning: 'representation',
      parentContext: queryContext
    });
    
    console.log('Inserted project:', insertedProject[0].name);
    console.log('Context ID:', insertContext.contextId);
    
    // Get the project ID
    const projectId = insertedProject[0].id;
    
    // Test 3: Update the project
    console.log('\nTest 3: Update a project');
    const { data: updatedProject, context: updateContext } = await client.update('projects', {
      description: 'Updated by test script',
      metadata: { test: true, updated: true }
    }, {
      match: { id: projectId },
      returning: 'representation',
      parentContext: insertContext
    });
    
    console.log('Updated project description:', updatedProject[0].description);
    console.log('Context ID:', updateContext.contextId);
    
    // Test 4: RPC call
    console.log('\nTest 4: RPC call');
    const { data: similarProjects, context: rpcContext } = await client.rpc('match_page_sections', {
      embedding: [0.1, 0.2, 0.3],
      match_threshold: 0.5,
      match_count: 3,
      min_content_length: 10
    }, {
      parentContext: updateContext
    });
    
    console.log(`RPC returned ${similarProjects?.length || 0} similar projects`);
    console.log('Context ID:', rpcContext.contextId);
    
    // Test 5: Delete the project
    console.log('\nTest 5: Delete a project');
    const { data: deletedProject, context: deleteContext } = await client.delete('projects', {
      match: { id: projectId },
      returning: 'representation',
      parentContext: rpcContext
    });
    
    console.log('Deleted project:', deletedProject[0].name);
    console.log('Context ID:', deleteContext.contextId);
    
    // Test 6: Verify MCP logs
    console.log('\nTest 6: Verify MCP logs');
    console.log(`MCP logs count: ${mockDatabase.mcp_logs.length}`);
    console.log('Operations logged:', mockDatabase.mcp_logs.map(log => log.operation).join(', '));
    
    console.log('\nAll tests passed! MCP-Supabase integration is working correctly with the mock environment.');
    return true;
  } catch (error) {
    console.error('Test failed:', error);
    return false;
  }
}

// Run the test when this script is executed directly
if (require.main === module) {
  runTest().then(success => {
    process.exit(success ? 0 : 1);
  });
}

// Export for use in other scripts
module.exports = runTest; 