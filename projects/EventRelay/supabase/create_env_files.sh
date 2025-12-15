#!/bin/bash

# Create Supabase MCP environment files

# Create the config directory
mkdir -p ~/.config/supabase-mcp
mkdir -p mcp-supabase-frontend

# Create .env file in ~/.config/supabase-mcp
cat > ~/.config/supabase-mcp/.env << EOL
NEXT_PUBLIC_SUPABASE_URL=http://localhost:5432
NEXT_PUBLIC_SUPABASE_ANON_KEY=local_development_key
SUPABASE_SERVICE_ROLE_KEY=local_development_key
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mcp_supabase
EOL

# Create .env.local file in mcp-supabase-frontend
cat > mcp-supabase-frontend/.env.local << EOL
NEXT_PUBLIC_SUPABASE_URL=http://localhost:5432
NEXT_PUBLIC_SUPABASE_ANON_KEY=local_development_key
SUPABASE_SERVICE_ROLE_KEY=local_development_key
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mcp_supabase
EOL

echo "Environment files created successfully!"
echo "- ~/.config/supabase-mcp/.env"
echo "- mcp-supabase-frontend/.env.local" 