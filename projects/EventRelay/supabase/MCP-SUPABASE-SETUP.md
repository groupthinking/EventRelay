# MCP-Supabase Setup Guide

This guide explains how to set up and use the MCP-Supabase integration, which allows you to interact with Supabase using the Model Context Protocol (MCP) framework.

## Overview

The MCP-Supabase integration provides:

1. **SupabaseMcpClient**: A client for direct interaction with Supabase with full MCP context tracking
2. **Mock Environment**: A mock implementation for development and testing without requiring a real Supabase database
3. **Environment Setup**: Scripts to set up the required environment for real or mock Supabase integration

## Setup Options

### Option 1: Local PostgreSQL with Docker (Recommended)

This option runs a PostgreSQL container using Docker and initializes it with the Supabase schema.

1. Ensure Docker and Docker Compose are installed
2. Run the setup script:
   ```bash
   ./setup_local_env.sh
   ```
3. This will:
   - Start a PostgreSQL container
   - Set up environment variables
   - Create a `.env.local` file with connection details

### Option 2: Mock Environment (No Database Required)

This option uses an in-memory mock implementation of Supabase, useful for development and testing.

1. No setup required! The system will automatically fall back to the mock implementation if:
   - No Supabase credentials are found in environment variables
   - The Supabase client cannot be initialized
   - The database connection fails

## Testing the Integration

The MCP-Supabase integration can work with both real Supabase instances and a mock implementation.

### Quick Test with Mock Implementation

```bash
npm test
```

This runs a test against the mock implementation which doesn't require a real database connection.

### Testing with Real Supabase

```bash
npm run test-real
```

This tests the connection to a real Supabase instance and falls back to the mock implementation if the real connection fails.

### Setting Up Local PostgreSQL for Testing

If you don't have access to a real Supabase instance, you can set up a local PostgreSQL database with the required schema:

```bash
./setup_postgres_local.sh
```

This script:
1. Checks if PostgreSQL is installed and running
2. Creates a `mcp_supabase` database
3. Sets up the schema from `supabase_setup.sql`
4. Creates a `.env.local` file with connection details
5. Tests the connection

After running this script, you can run `npm run test-real` to test with the real PostgreSQL database.

## Configuration

### Environment Variables

The following environment variables are used:

- `NEXT_PUBLIC_SUPABASE_URL`: URL of the Supabase instance
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Anonymous key for Supabase
- `SUPABASE_URL`: Alternative URL for server-side code
- `SUPABASE_KEY`: Alternative key for server-side code

These can be set in a `.env.local` file or in the environment.

### Config Directory

For more flexible configuration, you can create a config file at:

```
~/.config/supabase-mcp/.env
```

## Using the Integration

### Basic Example

```javascript
import SupabaseMcpClient from './lib/supabase_mcp_client';
import { createMcpContext } from './lib/mcp';

// Create a context
const context = createMcpContext('my_operation', 'my-app', {
  // Operation parameters
  param1: 'value1',
  param2: 'value2'
});

// Create a client
const client = new SupabaseMcpClient({
  source: 'my-app',
  parentContext: context
});

// Query data
const { data, error, context: resultContext } = await client.query('my_table', {
  filters: { status: 'active' },
  limit: 10
});

// Log the result
console.log(`Found ${data.length} records with context ID: ${resultContext.contextId}`);
```

### Multi-Step Workflow Example

See `lib/supabase_mcp_examples.js` for a complete example of a multi-step workflow with context propagation.

## Components

### Main Components

- `lib/supabase_mcp_client.js`: The SupabaseMcpClient class
- `lib/mcp_enhancer.js`: MCP enhancements for Supabase
- `lib/supabase.js`: Supabase client with automatic fallback to mock
- `lib/mock_supabase_env.js`: Mock implementation of Supabase

### Test and Demo Components

- `test_mcp_supabase_mock.js`: Test script
- `public/mcp-supabase-demo.html`: Browser-based demo
- `pages/api/mcp-supabase.js`: API endpoint for MCP-Supabase operations
- `pages/api/admin/logs.js`: API endpoint for querying MCP logs

## Troubleshooting

### Connection Issues

If you're having trouble connecting to Supabase:

1. Check if the `.env.local` file exists with the correct credentials
2. Verify that the PostgreSQL container is running:
   ```bash
   docker ps | grep postgres
   ```
3. Try running the test script to see if the mock environment works

### Mock Mode

To force the system to use the mock implementation, even if Supabase is available:

```javascript
// In lib/supabase.js
let isUsingMock = true;
```

## Next Steps

- Set up authentication with Supabase Auth
- Implement more sophisticated search options
- Create admin dashboard for MCP logs
- Set up proper RLS policies for production 