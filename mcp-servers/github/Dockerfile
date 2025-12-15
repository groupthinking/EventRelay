FROM node:18-alpine

WORKDIR /app

# Install GitHub MCP server
RUN npm install -g @modelcontextprotocol/server-github@2025.4.8

# Set the entrypoint to the server
ENTRYPOINT ["@modelcontextprotocol/server-github"]
