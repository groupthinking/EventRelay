# Multi-stage build for Universal Automation Service
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies (build tools for some python packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Copy project files
COPY . .

# EventRelay dependencies are tricky because they are local path imports in the script.
# We need to copy them into the container context if we want to build a self-contained image.
# For this 'dev' setup, we might assume volume mounting, but production needs copying.
# Let's assume we copy the necessary directories.
COPY projects/EventRelay /app/projects/EventRelay
COPY projects/UVAI /app/projects/UVAI

# Set PYTHONPATH so the imports in universal_coordinator.py work
ENV PYTHONPATH="${PYTHONPATH}:/app/projects/EventRelay/src:/app/projects/UVAI/src"

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install Node.js for MCP servers (puppeteer, unified-analytics)
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy python env from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy app code
COPY --from=builder /app /app

# Expose ports for MCP Bridge/Orchestrator if needed
EXPOSE 8001
EXPOSE 8004

# Default command
CMD ["python3", "universal-automation-service/universal_coordinator.py", "--help"]
