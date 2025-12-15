#!/bin/bash

# Set up local environment for MCP-Supabase integration

echo "Setting up local environment for MCP-Supabase integration..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker to continue."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose to continue."
    exit 1
fi

# Start PostgreSQL container
echo "Starting PostgreSQL container..."
docker-compose up -d

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 10

# Set up environment variables
export SUPABASE_URL="postgresql://postgres:postgres@localhost:5432/mcp_supabase"
export SUPABASE_KEY="local_development_key"

# Create local env file for Next.js
cat > .env.local << EOL
NEXT_PUBLIC_SUPABASE_URL=http://localhost:5432
NEXT_PUBLIC_SUPABASE_ANON_KEY=local_development_key
SUPABASE_URL=postgresql://postgres:postgres@localhost:5432/mcp_supabase
SUPABASE_KEY=local_development_key
EOL

echo "Local environment setup complete!"
echo "You can now use the MCP-Supabase integration with a local PostgreSQL database."
echo ""
echo "To connect to the database manually:"
echo "  - Host: localhost"
echo "  - Port: 5432"
echo "  - User: postgres"
echo "  - Password: postgres"
echo "  - Database: mcp_supabase"
echo ""
echo "Environment variables exported for this session:"
echo "  - SUPABASE_URL: $SUPABASE_URL"
echo "  - SUPABASE_KEY: $SUPABASE_KEY"
echo ""
echo "A .env.local file has been created for Next.js." 