# Dockerfile for UVAI Backend - Cloud Run Optimized
# Multi-stage build for smaller image size

# Stage 1: Builder
FROM python:3.11-slim AS builder

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
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1000 uvai && \
    useradd --uid 1000 --gid uvai --shell /bin/bash --create-home uvai

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=uvai:uvai src/ ./src/
COPY --chown=uvai:uvai pyproject.toml ./

# Create data directories
RUN mkdir -p /app/data/enhanced_analysis /app/data/cache /app/logs && \
    chown -R uvai:uvai /app/data /app/logs

# Switch to non-root user
USER uvai

# Environment variables for Cloud Run
ENV PORT=8080
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src

# Expose the Cloud Run default port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v1/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "youtube_extension.backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
