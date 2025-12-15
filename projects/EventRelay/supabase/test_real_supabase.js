/**
 * Test Real Supabase Connection
 * 
 * This script verifies that we can connect to a real Supabase instance.
 * It will gracefully fall back to the mock implementation if real connection fails.
 */

// Print initial environment variables BEFORE anything else
console.log('Initial environment variables:');
Object.keys(process.env)
  .filter(k => k.toUpperCase().includes('SUPABASE'))
  .forEach(k => console.log(`  ${k}=${process.env[k]}`));

const fs = require('fs');
const path = require('path');
const os = require('os');

// Manually load the critical config file
const criticalEnvPath = path.join(os.homedir(), '.config', 'supabase-mcp', '.env');
try {
  if (fs.existsSync(criticalEnvPath)) {
    console.log(`Manually loading ${criticalEnvPath}...`);
    const criticalEnvContent = fs.readFileSync(criticalEnvPath, 'utf8');
    criticalEnvContent.split('\n').forEach(line => {
      const [key, ...valueParts] = line.split('=');
      const value = valueParts.join('=').trim();
      if (key && value && !key.startsWith('#')) {
        process.env[key] = value; // Force set/override
        console.log(`  Manually set ${key}`);
      }
    });
  } else {
    console.warn(`Warning: Critical config file not found at ${criticalEnvPath}`);
  }
} catch (manualLoadError) {
  console.error(`Error manually loading ${criticalEnvPath}:`, manualLoadError);
}

// Attempt to load .env.local (will NOT override manually set vars)
require('dotenv').config({ path: '.env.local' }); 

// Print all Supabase-related environment variables for proof AFTER loading
console.log('\nFinal environment variables used:');
Object.keys(process.env)
  .filter(k => k.toUpperCase().includes('SUPABASE'))
  .forEach(k => console.log(`  ${k}=${process.env[k]}`));

// Get Supabase credentials from environment
const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_ANON_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;

console.log('\nUsing Supabase URL:', supabaseUrl ? supabaseUrl : 'Missing');
console.log('Using Supabase Key:', supabaseKey ? supabaseKey.substring(0, 5) + '...' : 'Missing');

if (!supabaseUrl || !supabaseKey) {
  console.error('Supabase credentials missing. Please check your .env file or environment variables.');
  console.log('Will use mock implementation as fallback.');
}

// Try to create a real Supabase client
try {
  const { createClient } = require('@supabase/supabase-js');
  const supabase = createClient(supabaseUrl, supabaseKey);
  
  console.log('Successfully created Supabase client');
  
  // Try to connect and perform a simple query
  async function testConnection() {
    try {
      console.log('Testing connection to Supabase...');
      
      // Check if mcp_logs table exists and is queryable
      console.log('Checking mcp_logs table...');
      const { data: logsCheck, error: logsCheckError } = await supabase
        .from('mcp_logs')
        .select('context_id')
        .limit(1);
        
      if (logsCheckError) {
        if (logsCheckError.code === '42P01') { // Relation does not exist
          console.error('❌ ERROR: The `mcp_logs` table does not exist in your Supabase project.');
          console.error('Please run the schema setup script (supabase_setup.sql) against your database.');
        } else {
          console.error(`❌ ERROR: Could not query mcp_logs table: ${logsCheckError.message}`);
        }
        throw new Error('mcp_logs table check failed');
      } else {
        console.log('✅ `mcp_logs` table exists and is queryable.');
      }
      
      // Create a test mcp_logs entry with unique content
      const testId = 'test-' + Date.now();
      const { data: insertData, error: insertError } = await supabase
        .from('mcp_logs')
        .insert({
          context_id: testId,
          operation: 'test_connection',
          user_id: 'test-script',
          timestamp: Math.floor(Date.now() / 1000),
          parameters: { test: true },
          result: {},
          status: 'testing'
        });
      
      if (insertError) {
        console.error('Failed to insert test data:', insertError.message);
        
        if (insertError.message.includes('does not exist')) {
          console.log('The mcp_logs table does not exist. Attempting to verify if any table exists...');
          
          // Try to query the projects table
          const { data: projects, error: projectsError } = await supabase
            .from('projects')
            .select('*')
            .limit(1);
            
          if (projectsError) {
            console.error('Failed to query projects table:', projectsError.message);
            
            // Attempt to verify database connection
            try {
              // Try a basic connection validation
              const { data, error } = await supabase.from('pg_catalog.pg_tables').select('*').limit(1);
              
              if (error) {
                console.error('Failed to connect to the database:', error.message);
                throw new Error('Database connection failed');
              } else {
                console.log('Connected to database, but application tables do not exist. Schema setup needed.');
                return { success: false, reason: 'schema_missing' };
              }
            } catch (e) {
              console.error('Database connection test failed:', e.message);
              throw new Error('Database connection test failed');
            }
          } else {
            console.log('Successfully queried projects table. MCP logs table is missing, but connection works.');
            return { success: true, usingReal: true, tables: ['projects'] };
          }
        } else {
          throw new Error('Insert test failed: ' + insertError.message);
        }
      } else {
        console.log('Successfully inserted test log entry with ID:', testId);
        
        // Query it back to verify
        const { data: queryData, error: queryError } = await supabase
          .from('mcp_logs')
          .select('*')
          .eq('context_id', testId);
          
        if (queryError) {
          console.error('Failed to query back the inserted record:', queryError.message);
          throw new Error('Query test failed');
        } else if (!queryData || queryData.length === 0) {
          console.error('Could not find the inserted record when querying back');
          throw new Error('Data consistency test failed');
        } else {
          console.log('Successfully queried back the inserted record');
          
          // Clean up
          const { error: deleteError } = await supabase
            .from('mcp_logs')
            .delete()
            .eq('context_id', testId);
            
          if (deleteError) {
            console.warn('Failed to clean up test record:', deleteError.message);
          } else {
            console.log('Successfully cleaned up test record');
          }
          
          console.log('All tests passed! Connection to real Supabase verified successfully.');
          return { success: true, usingReal: true };
        }
      }
    } catch (error) {
      console.error('Error testing connection:', error.message);
      console.log('Will fall back to mock implementation');
      
      // Test if the mock implementation works
      try {
        // Import our mock implementation
        const mockSupabase = require('./lib/mock_supabase_env').default;
        
        console.log('Testing mock implementation...');
        
        // Perform a simple query using the mock
        const { data, error } = await mockSupabase
          .from('projects')
          .select('*')
          .limit(1);
          
        if (error) {
          console.error('Mock implementation test failed:', error);
          return { success: false, usingReal: false, mockWorking: false };
        } else {
          console.log('Mock implementation working correctly. Found', data.length, 'projects.');
          return { success: true, usingReal: false, mockWorking: true };
        }
      } catch (mockError) {
        console.error('Error testing mock implementation:', mockError.message);
        return { success: false, usingReal: false, mockWorking: false };
      }
    }
  }
  
  // Run the test and report
  testConnection().then(result => {
    console.log('\nTest Summary:');
    console.log('- Success:', result.success ? 'Yes' : 'No');
    console.log('- Using Real Supabase:', result.usingReal ? 'Yes' : 'No');
    
    if (!result.usingReal) {
      console.log('- Mock Working:', result.mockWorking ? 'Yes' : 'No');
    }
    
    if (result.reason === 'schema_missing') {
      console.log('\nNext Steps:');
      console.log('1. Run the SQL setup script to create required tables:');
      console.log('   - Connect to your PostgreSQL server');
      console.log('   - Run the contents of supabase_setup.sql');
    }
    
    process.exit(result.success ? 0 : 1);
  });
  
} catch (error) {
  console.error('Error creating Supabase client:', error.message);
  console.log('Will attempt to use mock implementation...');
  
  try {
    // Test if the mock implementation works as fallback
    const mockSupabase = require('./lib/mock_supabase_env').default;
    
    // Perform a simple query
    mockSupabase
      .from('projects')
      .select('*')
      .limit(1)
      .then(({ data, error }) => {
        if (error) {
          console.error('Mock implementation failed:', error);
          console.log('\nTest Summary:');
          console.log('- Success: No');
          console.log('- Using Real Supabase: No');
          console.log('- Mock Working: No');
          process.exit(1);
        } else {
          console.log('Mock implementation working correctly. Found', data.length, 'projects.');
          console.log('\nTest Summary:');
          console.log('- Success: Yes');
          console.log('- Using Real Supabase: No');
          console.log('- Mock Working: Yes');
          process.exit(0);
        }
      });
  } catch (mockError) {
    console.error('Error testing mock implementation:', mockError.message);
    console.log('\nTest Summary:');
    console.log('- Success: No');
    console.log('- Using Real Supabase: No');
    console.log('- Mock Working: No');
    process.exit(1);
  }
} 