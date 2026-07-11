# Dockerfile for EventRelay Web Application (Next.js)
# Optimized for npm workspaces and production performance

# Stage 1: Base image
FROM node:22-slim AS base
WORKDIR /app

# Stage 2: Install dependencies
FROM base AS deps
# Install system dependencies if any are needed for node-gyp etc.
# RUN apt-get update && apt-get install -y python3 make g++ && rm -rf /var/lib/apt/lists/*

# Copy root workspace files
COPY package.json package-lock.json ./

# Copy workspace package.json
COPY apps/web/package.json ./apps/web/

# Copy the file: dependency sources required by package.json manifests
COPY src/dataconnect-generated ./src/dataconnect-generated
COPY apps/web/src/dataconnect-generated ./apps/web/src/dataconnect-generated

# Install dependencies for the workspace at the root level
# This ensures package-lock.json is respected and hoisting works correctly
RUN npm ci --workspace=apps/web --legacy-peer-deps

# Stage 3: Builder
FROM base AS builder
WORKDIR /app

# Copy installed dependencies from deps stage
COPY --from=deps /app ./

# Copy the rest of the application source code
COPY . .

# Build the Next.js application
RUN npm run build --workspace=apps/web

# Stage 4: Runner
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

RUN groupadd --gid 1001 nodejs && \
    useradd --uid 1001 --gid nodejs --shell /bin/bash --create-home nextjs

# Copy necessary files for running the app
# We copy the root node_modules and app node_modules because of hoisting
COPY --from=builder /app/package.json ./
COPY --from=builder /app/apps/web/package.json ./apps/web/
COPY --from=builder /app/node_modules ./node_modules
# Use a wildcard copy to handle cases where apps/web/node_modules might be absent due to total hoisting
COPY --from=builder /app/apps/web/node_modules* ./apps/web/node_modules/
COPY --from=builder /app/apps/web/.next ./apps/web/.next
COPY --from=builder /app/apps/web/public ./apps/web/public
COPY --from=builder /app/apps/web/next.config.js ./apps/web/

# Copy the file: dependency sources to avoid dangling symlinks in node_modules
COPY --from=builder /app/src/dataconnect-generated ./src/dataconnect-generated
COPY --from=builder /app/apps/web/src/dataconnect-generated ./apps/web/src/dataconnect-generated

USER nextjs

EXPOSE 3000

# Start the application from the workspace directory
WORKDIR /app/apps/web
# Use shell-form for consistent behavior with the backend and PORT support
CMD npx next start
