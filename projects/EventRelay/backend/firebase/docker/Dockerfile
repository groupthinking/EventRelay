# Multi-stage Docker build for Firebase Project
# Optimized for Phase 3 systems with analytics, AI, and compliance

# ===== BUILD STAGE =====
FROM node:18-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    python3 \
    make \
    g++ \
    git \
    curl \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /app

# Copy package files for dependency installation
COPY package*.json ./
COPY yarn.lock* ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Copy source code
COPY . .

# Build application (if needed)
RUN npm run build 2>/dev/null || echo "No build script found"

# ===== PRODUCTION STAGE =====
FROM node:18-alpine AS production

# Install runtime dependencies
RUN apk add --no-cache \
    curl \
    wget \
    ca-certificates \
    openssl \
    && rm -rf /var/cache/apk/*

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S firebase -u 1001

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Copy built application from builder stage
COPY --from=builder --chown=firebase:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=firebase:nodejs /app/dist ./dist
COPY --from=builder --chown=firebase:nodejs /app/src ./src
COPY --from=builder --chown=firebase:nodejs /app/Docs ./Docs
COPY --from=builder --chown=firebase:nodejs /app/config ./config
COPY --from=builder --chown=firebase:nodejs /app/scripts ./scripts

# Copy additional directories
COPY --chown=firebase:nodejs integrations ./integrations
COPY --chown=firebase:nodejs monitoring ./monitoring
COPY --chown=firebase:nodejs analytics ./analytics
COPY --chown=firebase:nodejs ai-docs ./ai-docs
COPY --chown=firebase:nodejs compliance ./compliance
COPY --chown=firebase:nodejs risk-assessment ./risk-assessment

# Create necessary directories with proper permissions
RUN mkdir -p \
    /app/logs \
    /app/monitoring/metrics \
    /app/monitoring/alerts \
    /app/analytics/data \
    /app/reports \
    /app/test-results \
    && chown -R firebase:nodejs /app

# Switch to non-root user
USER firebase

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Expose ports
EXPOSE 3000

# Environment variables
ENV NODE_ENV=production \
    PORT=3000 \
    NODE_OPTIONS="--max-old-space-size=4096"

# Start application
CMD ["npm", "start"]
