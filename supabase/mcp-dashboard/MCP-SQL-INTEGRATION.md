# SQL Integration with MCP Framework

This document outlines how the Model Context Protocol (MCP) Framework integrates with SQL databases, allowing AI models to access structured data from databases as context.

## Overview

The SQL integration enables:

1. Extracting query results as structured MCP context
2. Capturing database schema information
3. Tracking performance metrics for queries
4. Sanitizing sensitive connection information
5. Visualizing SQL contexts alongside other context types

## Setup

### Prerequisites

- Node.js (v14+)
- PostgreSQL database (local or remote)
- MCP Framework

### Installation

1. Install the required dependencies:

```bash
npm install
```

2. Set up your PostgreSQL environment:

```bash
# Set environment variables for your database connection
./setup_postgres_local.sh

# Or manually set them
export PGHOST="localhost"
export PGPORT=5432
export PGDATABASE="postgres"
export PGUSER="postgres"
export PGPASSWORD="yourpassword"
```

3. For Docker users, you can start a PostgreSQL container:

```bash
docker run --name mcp-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=postgres \
  -p 5432:5432 \
  -d postgres:14
```

## Usage

### Running the SQL Integration Test

Execute the integration test script:

```bash
npm run test-sql
```

This will:
- Connect to the PostgreSQL database
- Create a test table if it doesn't exist
- Run sample queries
- Extract MCP context from each query
- Combine the contexts
- Generate a visualization

### Using SQL Extractor in Your Code

```javascript
const { MCPOrchestrator } = require('./mcp-orchestrator');
const { Client } = require('pg');

// Initialize the MCP Orchestrator
const orchestrator = new MCPOrchestrator({
  visualize: true,
  persistence: { enabled: true }
});

// Connect to PostgreSQL
const client = new Client({
  host: process.env.PGHOST,
  port: process.env.PGPORT,
  database: process.env.PGDATABASE,
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD
});
await client.connect();

// Execute a query
const query = 'SELECT * FROM users WHERE status = $1 LIMIT 100';
const queryResult = await client.query(query, ['active']);

// Extract MCP context from the query results
const sqlContext = await orchestrator.extract('sql', {
  query,
  results: queryResult.rows,
  connection: {
    host: client.host,
    database: client.database,
    user: client.user
    // password is intentionally omitted for security
  },
  metadata: {
    executionTime: 123, // milliseconds
    timestamp: new Date().toISOString()
  }
});

console.log(`SQL context extracted: ${sqlContext.context_id}`);
```

## Architecture

The SQL integration consists of:

1. **SQL Extractor**: Processes query results into MCP contexts
2. **Schema Helper**: Captures database schema information
3. **Stats Helper**: Retrieves database statistics
4. **Sanitization Layer**: Removes sensitive information like passwords

## MCP Context Structure

The SQL extractor generates an MCP context with this structure:

```json
{
  "context_id": "sql-[uuid]",
  "operation": "extract",
  "parameters": {
    "source": "sql",
    "query": "SELECT * FROM users",
    "database": "my_database"
  },
  "result": {
    "query": "SELECT * FROM users",
    "results": [{...}, {...}],
    "rowCount": 2,
    "execution": {
      "timestamp": "2023-07-22T15:30:00.000Z",
      "duration": 123
    },
    "connection": {
      "host": "localhost",
      "database": "my_database",
      "user": "db_user"
    },
    "schema": {
      "tables": [{
        "name": "users",
        "columns": [
          { "name": "id", "type": "integer", "primary": true },
          { "name": "name", "type": "varchar(255)" },
          { "name": "created_at", "type": "timestamp" }
        ]
      }]
    }
  },
  "metadata": {
    "extractionTime": "2023-07-22T15:30:00.100Z",
    "extractorVersion": "1.0.0"
  }
}
```

## Security Considerations

The SQL integration automatically:

1. Sanitizes connection information (removes passwords)
2. Allows parameterized queries to prevent SQL injection
3. Applies access control to contexts with sensitive data

## Future Enhancements

- Support for other database types (MySQL, SQLite, MongoDB)
- Query plan extraction and optimization suggestions
- Database health metrics as part of context
- Integration with database migration tools

## Troubleshooting

### Common Issues

**Connection Failure**
- Verify PostgreSQL is running: `pg_isready -h localhost`
- Check environment variables are set correctly
- Ensure database credentials are correct

**Integration Test Fails**
- Check the log file at `sql_mcp_test_log.txt`
- Verify the test database has enough permissions to create tables
- Check for any dependency issues

**Performance Problems**
- Limit the result set size for large queries
- Consider adding indexes to frequently queried tables
- Use the `schema` parameter to add schema context without additional queries 