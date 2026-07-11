# Dockerfile for EventRelay - Hybrid Python + Node.js (v22)
# Fixes: "ffmpeg not found" and "npm: command not found" production errors
# Multi-stage build optimized for production

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system build deps + ffmpeg + Node.js 22 LTS in a single layer
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

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir -e .; \
    fi

# Install Node.js dependencies for the web app
# Using workspace to ensure proper hoisting and dependency resolution
RUN npm ci --workspace=apps/web --production --legacy-peer-deps

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create non-root user (UID 1000)
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Install runtime system deps: ffmpeg + Node.js 22 LTS + curl (for health check)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    gnupg \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

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

# Runtime data directories
RUN mkdir -p /app/data/enhanced_analysis /app/data/cache /app/logs \
             /app/generated_projects /app/youtube_processed_videos /tmp/uvai_data && \
    chown -R appuser:appuser /app/data /app/logs /app/generated_projects \
                              /app/youtube_processed_videos /tmp/uvai_data

USER appuser

# Environment variables
ENV PORT=8080 \
    HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    NODE_ENV=production

EXPOSE ${PORT}

# Health check using curl (installed above)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# Run — shell form so $PORT is expanded at runtime
CMD python -m uvicorn youtube_extension.main:app --host 0.0.0.0 --port ${PORT}
