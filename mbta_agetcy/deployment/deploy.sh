#!/bin/bash

# MBTA-Corto Deployment Script
set -e

echo "🚀 Deploying MBTA-Corto System"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
else
    echo "⚠️  .env file not found. Creating from template..."
    cat > .env << EOF
ANTHROPIC_API_KEY=your_key_here
CLICKHOUSE_PASSWORD=clickhouse
EOF
    echo "Please edit .env with your API keys"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Build and start services
echo "📦 Building Docker images..."
docker-compose -f docker/docker-compose.yml build

echo "🚀 Starting services..."
docker-compose -f docker/docker-compose.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check health endpoints
echo "🏥 Checking service health..."

check_health() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null; then
            echo "✅ $service is healthy"
            return 0
        fi
        echo "⏳ Waiting for $service... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    echo "❌ $service failed to become healthy"
    return 1
}

check_health "Exchange Agent" "http://localhost:8100/health"
check_health "MBTA Orchestrator" "http://localhost:8101/health"
check_health "Frontend" "http://localhost:3000/health"
check_health "Grafana" "http://localhost:3001/api/health"

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📍 Service URLs:"
echo "   - Frontend UI:        http://localhost:3000"
echo "   - Exchange Agent:     http://localhost:8100"
echo "   - MBTA Orchestrator:  http://localhost:8101"
echo "   - Grafana:            http://localhost:3001 (admin/admin)"
echo "   - Prometheus:         http://localhost:9090"
echo "   - ClickHouse:         http://localhost:8123"
echo ""
echo "📊 To view logs:"
echo "   docker-compose -f docker/docker-compose.yml logs -f"
echo ""
echo "🛑 To stop:"
echo "   docker-compose -f docker/docker-compose.yml down"