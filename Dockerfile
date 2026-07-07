# Dockerfile for EventRelay — ffmpeg + Node.js v22 + multi-stage build
# Fixes: "ffmpeg not found" and "npm: command not found" production errors

# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system build deps + ffmpeg + Node.js 22 LTS in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        gnupg \
        ffmpeg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt* pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir --upgrade pip && \
    if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir -e .; \
    fi

# Node deps (production only)
COPY apps/web/package.json apps/web/package-lock.json apps/web/
RUN cd apps/web && npm ci --production --ignore-scripts

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create non-root user (UID 1000)
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Install runtime system deps: ffmpeg + Node.js 22 LTS + curl (for health check)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        ffmpeg \
        gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy Python site-packages and binaries from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser pyproject.toml ./

# Copy Node artifacts from builder
COPY --chown=appuser:appuser --from=builder /app/apps/web/node_modules ./apps/web/node_modules

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
CMD python -m uvicorn youtube_extension.main:app --host 0.0.0.0 --port $PORT
