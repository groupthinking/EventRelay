FROM python:3.11-slim

# Install system dependencies including those needed for Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get update && apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY requirements.txt ./
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy package.json/package-lock.json and run npm ci
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of the source code
COPY . .

# Set PYTHONPATH so that youtube_extension can be imported
ENV PYTHONPATH=/app/src

EXPOSE 8080

# Run
CMD ["python", "-m", "uvicorn", "youtube_extension.main:app", "--host", "0.0.0.0", "--port", "8080"]
