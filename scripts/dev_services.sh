#!/bin/bash
# scripts/dev_services.sh
# Starts local development dependencies (Postgres, Redis, RabbitMQ) via Docker Compose.

set -e

echo "🐳 Starting development services..."

# Ensure infrastructure directory exists preventing bind mount errors
mkdir -p infrastructure/database

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
  echo "❌ Docker is not running. Please start Docker Desktop and try again."
  exit 1
fi

# Start services in detached mode
docker-compose -f docker-compose.full.yml up -d postgres redis rabbitmq

echo "✅ Services started!"
echo "   - Postgres: localhost:5432"
echo "   - Redis:    localhost:6379"
echo "   - RabbitMQ: localhost:5672 (UI: http://localhost:15672)"
echo ""
echo "To stop services: docker-compose -f docker-compose.full.yml down"
