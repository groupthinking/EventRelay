# Dockerfile.production
# Production-optimized build for EventRelay on Google Cloud Run
# Supports dynamic PORT binding and multi-stage build optimization

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy all files (matches existing Dockerfile pattern)
COPY . /app/

# Install Python packages using pyproject.toml
# Install core dependencies needed for production
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org \
    -e .[youtube,ml]

# Create necessary directories and set permissions
RUN mkdir -p logs && \
    chown -R appuser:appuser /app

# Health check (uses PORT environment variable)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/v1/health || curl -f http://localhost:${PORT:-8000}/health || exit 1

# Switch to non-root user
USER appuser

# Expose port (Cloud Run will override with $PORT)
EXPOSE 8000

# Start the application with PORT environment variable support
# Cloud Run sets $PORT dynamically, default to 8000 for local testing
CMD ["python", "-m", "uvicorn", "uvai.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]