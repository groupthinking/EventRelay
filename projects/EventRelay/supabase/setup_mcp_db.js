/**
 * MCP Database Setup Script
 * 
 * This script sets up the necessary database tables for the MCP framework.
 * It checks if the tables already exist and creates them if they don't.
 */

// Import config
const config = require('./lib/config');
const { createClient } = require('@supabase/supabase-js');

console.log('Setting up MCP database...');
console.log('Using Supabase URL:', config.SUPABASE.URL);

// Create Supabase client
const supabase = createClient(config.SUPABASE.URL, config.SUPABASE.ANON_KEY);

async function setupDatabase() {
  try {
    // Check if mcp_contexts table exists
    console.log('Checking if mcp_contexts table exists...');
    
    const { data: tables, error: tablesError } = await supabase
      .from('information_schema.tables')
      .select('table_name')
      .eq('table_schema', 'public')
      .eq('table_name', 'mcp_contexts');
    
    if (tablesError) {
      console.error('Error checking tables:', tablesError.message);
      throw tablesError;
    }
    
    if (tables && tables.length > 0) {
      console.log('mcp_contexts table already exists.');
      
      // Check if we can query from it
      const { data: contexts, error: contextsError } = await supabase
        .from('mcp_contexts')
        .select('context_id')
        .limit(1);
      
      if (contextsError) {
        console.error('Error querying mcp_contexts:', contextsError.message);
        
        if (contextsError.code === '42P01') { // Relation does not exist
          console.log('Table exists in schema but might be in another schema. Creating table...');
          await createTables();
        } else {
          throw contextsError;
        }
      } else {
        console.log('Successfully queried mcp_contexts table.');
        console.log('Contexts found:', contexts.length);
      }
    } else {
      console.log('mcp_contexts table does not exist. Creating table...');
      await createTables();
    }
    
    console.log('Database setup complete!');
  } catch (error) {
    console.error('Error setting up database:', error.message);
    process.exit(1);
  }
}

async function createTables() {
  // Create mcp_contexts table using supabase's SQL function
  const { error } = await supabase.rpc('exec_sql', {
    sql_string: `
      CREATE TABLE IF NOT EXISTS mcp_contexts (
        id SERIAL PRIMARY KEY,
        context_id TEXT UNIQUE NOT NULL,
        operation TEXT NOT NULL,
        parameters JSONB,
        result JSONB,
        metadata JSONB,
        access_control JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
      );
      
      CREATE INDEX IF NOT EXISTS idx_mcp_contexts_context_id ON mcp_contexts (context_id);
      CREATE INDEX IF NOT EXISTS idx_mcp_contexts_operation ON mcp_contexts (operation);
      CREATE INDEX IF NOT EXISTS idx_mcp_contexts_created_at ON mcp_contexts (created_at);
    `
  });
  
  if (error) {
    // If exec_sql is not available, warn but continue
    console.warn('Could not use exec_sql function:', error.message);
    console.warn('You may need to create the tables manually using supabase_setup.sql');
  } else {
    console.log('Created mcp_contexts table successfully!');
  }
}

// Run the setup
setupDatabase(); 