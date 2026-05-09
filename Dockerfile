# Dockerfile for EventRelay Backend - Cloud Run Optimized
# Multi-stage build for smaller image size

# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

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

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1000 uvai && \
    useradd --uid 1000 --gid uvai --shell /bin/bash --create-home uvai

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    ffmpeg \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y --no-install-recommends nodejs \
    && npm install -g hyperframes@0.5.5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=uvai:uvai src/ ./src/
COPY --chown=uvai:uvai pyproject.toml ./

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
# HyperFrames rendering stays opt-in unless explicitly enabled in the runtime environment.
ENV HYPERFRAMES_ENABLED=false

EXPOSE ${PORT}

# Health check (uses PORT env var)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",8080)}/api/v1/health')" || exit 1

# Run — use shell form so $PORT is expanded at runtime
CMD python -m uvicorn youtube_extension.main:app --host 0.0.0.0 --port $PORT
