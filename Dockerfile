# Dockerfile for EventRelay — Multi-stage build
# Includes: Python 3.11, ffmpeg, Node.js 22 LTS
# Fixes: DownloadError (ffmpeg not found), npm: command not found

# ============================================================
# Stage 1: Builder — install Python + Node dependencies
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies (gcc for native Python extensions, curl/gnupg for NodeSource)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Node.js production dependencies (workspace: apps/web is the only workspace)
# Uses npm install because workspace package versions may drift from lockfile
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/
RUN npm install --omit=dev --ignore-scripts

# ============================================================
# Stage 2: Runtime — lean production image (< 1 GB)
# ============================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime system dependencies: ffmpeg, Node.js 22, curl (for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    gnupg \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy Node modules from builder
COPY --from=builder /app/node_modules node_modules

# Copy application source
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser apps/ ./apps/
COPY --chown=appuser:appuser pyproject.toml ./

# Create data directories
RUN mkdir -p /app/data/enhanced_analysis /app/data/cache /app/logs \
    /app/generated_projects /app/youtube_processed_videos /tmp/eventrelay_data && \
    chown -R appuser:appuser /app /tmp/eventrelay_data

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_ENV=production \
    PYTHONPATH=/app/src \
    PORT=8080 \
    HOST=0.0.0.0

EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Run application — shell form so $PORT is expanded at runtime
CMD python -m uvicorn youtube_extension.main:app --host 0.0.0.0 --port $PORT
