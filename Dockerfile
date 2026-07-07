# Dockerfile for EventRelay Backend - Cloud Run Optimized
# Multi-stage build for smaller image size

# Reuse the official Node image instead of piping an external install script to bash.
FROM node:20-bookworm-slim AS node

# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && \
    ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# Copy dependency files
COPY pyproject.toml ./
COPY requirements.txt* ./

# Copy source code for package installation (needed for editable installs)
COPY src/ ./src/

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir -e .; \
    fi

# Install the apps/web production workspace dependencies using the root lockfile
COPY package.json package-lock.json .npmrc ./
COPY apps/web/package.json ./apps/web/package.json
# apps/web depends on @dataconnect/generated via a local file: reference, so the
# generated source must exist before npm resolves the workspace dependency tree.
COPY apps/web/src/dataconnect-generated ./apps/web/src/dataconnect-generated
RUN npm ci --workspace apps/web --omit=dev --ignore-scripts

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1000 uvai && \
    useradd --uid 1000 --gid uvai --shell /bin/bash --create-home uvai

# Install runtime dependencies only (including Node.js/npm for build verification of generated projects)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && \
    ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=uvai:uvai src/ ./src/
COPY --chown=uvai:uvai pyproject.toml ./
COPY --chown=uvai:uvai apps/web/package.json ./apps/web/package.json
COPY --chown=uvai:uvai apps/web/src/dataconnect-generated ./apps/web/src/dataconnect-generated
COPY --chown=uvai:uvai --from=builder /app/apps/web/node_modules ./apps/web/node_modules

# Create data directories
RUN mkdir -p /app/data/enhanced_analysis /app/data/cache /app/logs /app/generated_projects /app/youtube_processed_videos /tmp/uvai_data && \
    chown -R uvai:uvai /app/data /app/logs /app/generated_projects /app/youtube_processed_videos /tmp/uvai_data

# Switch to non-root user
USER uvai

# Environment variables
ENV PORT=8080
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src

EXPOSE ${PORT}

# Health check (uses PORT env var)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",8080)}/api/v1/health')" || exit 1

# Run — use shell form so $PORT is expanded at runtime
CMD python -m uvicorn youtube_extension.main:app --host 0.0.0.0 --port $PORT
