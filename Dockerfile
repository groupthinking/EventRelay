# Dockerfile for EventRelay - Hybrid Python + Node.js (v22)
# Multi-stage build optimized for production

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    ffmpeg \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests
COPY pyproject.toml requirements.txt* ./
COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/

# Copy local file dependencies for npm workspace
COPY src/dataconnect-generated ./src/dataconnect-generated
COPY apps/web/src/dataconnect-generated ./apps/web/src/dataconnect-generated

# postinstall in apps/web/package.json runs
# `node scripts/patch-world-vercel-undici-fetch.mjs`. npm ci fails if the
# script is missing from the builder context (Security Scan / Trivy).
COPY apps/web/scripts ./apps/web/scripts

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    (pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir -e .)

# Install Node.js dependencies for the web app
# Using workspace to ensure proper hoisting and dependency resolution
RUN npm ci --workspace=apps/web --production --legacy-peer-deps

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime system dependencies (ffmpeg and nodejs v22)
# gnupg is required for the Nodesource setup script
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    gnupg \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy installed Node.js packages from builder
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/apps/web/node_modules ./apps/web/node_modules

# Copy local dataconnect artifacts to avoid dangling symlinks
COPY --from=builder /app/src/dataconnect-generated ./src/dataconnect-generated
COPY --from=builder /app/apps/web/src/dataconnect-generated ./apps/web/src/dataconnect-generated

# Copy application code with correct ownership
COPY --chown=appuser:appuser . .

# Imported API services persist local diagnostic files under ./logs. Prepare
# that ephemeral path before dropping privileges so application import cannot
# fail on Cloud Run's non-root runtime.
RUN mkdir -p /app/logs && chown appuser:appuser /app/logs

# Environment variables
ENV PORT=8080
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src
ENV NODE_ENV=production

USER appuser

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Default command (shell form for $PORT expansion)
CMD python -m uvicorn youtube_extension.main:app --host 0.0.0.0 --port ${PORT}
