#!/bin/bash

# Script to set up PostgreSQL environment variables for MCP SQL integration tests

echo "Setting up PostgreSQL environment variables for MCP SQL integration testing..."

# Default values - modify these as needed
export PGHOST="localhost"
export PGPORT=5432
export PGDATABASE="postgres"
export PGUSER="postgres"
export PGPASSWORD="postgres"

# If Docker is installed, offer to run PostgreSQL in Docker
if command -v docker &> /dev/null; then
  echo ""
  echo "Docker detected. Would you like to start a PostgreSQL container for testing? (y/n)"
  read -r start_docker

  if [[ "$start_docker" =~ ^[Yy]$ ]]; then
    echo "Starting PostgreSQL Docker container..."
    
    # Stop and remove existing container if it exists
    docker stop mcp-postgres 2>/dev/null
    docker rm mcp-postgres 2>/dev/null
    
    # Start PostgreSQL container
    docker run --name mcp-postgres \
      -e POSTGRES_PASSWORD=postgres \
      -e POSTGRES_USER=postgres \
      -e POSTGRES_DB=postgres \
      -p 5432:5432 \
      -d postgres:14
    
    if [ $? -eq 0 ]; then
      echo "PostgreSQL Docker container started successfully."
      echo "Waiting for PostgreSQL to be ready..."
      sleep 5
    else
      echo "Failed to start PostgreSQL Docker container."
      exit 1
    fi
  fi
fi

# Print current configuration
echo ""
echo "PostgreSQL Environment Configuration:"
echo "------------------------------------"
echo "Host:     $PGHOST"
echo "Port:     $PGPORT"
echo "Database: $PGDATABASE"
echo "User:     $PGUSER"
echo "Password: $PGPASSWORD"
echo ""

# Test database connection
echo "Testing database connection..."
if command -v pg_isready &> /dev/null; then
  pg_isready -h $PGHOST -p $PGPORT -U $PGUSER
  
  if [ $? -eq 0 ]; then
    echo "Database connection successful!"
  else
    echo "Could not connect to PostgreSQL database."
    echo "Please ensure PostgreSQL is running and credentials are correct."
  fi
else
  echo "pg_isready not found. Skipping connection test."
  echo "To test connection manually, run: npm run test-sql"
fi

echo ""
echo "Environment variables are set for the current shell session."
echo "To run the SQL integration test, use:"
echo "npm run test-sql"
echo ""
echo "If you want to persist these variables, add them to your .env file:"
echo "PGHOST=$PGHOST"
echo "PGPORT=$PGPORT"
echo "PGDATABASE=$PGDATABASE"
echo "PGUSER=$PGUSER"
echo "PGPASSWORD=$PGPASSWORD" 