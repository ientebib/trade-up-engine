#!/bin/bash
# Run the app in Docker to bypass macOS network restrictions

echo "=== Running Trade-Up Engine in Docker ==="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Build the image
echo "Building Docker image..."
docker build -f Dockerfile.dev -t tradeup-engine .

# Stop any existing container
docker stop tradeup-engine-dev 2>/dev/null
docker rm tradeup-engine-dev 2>/dev/null

# Run the container
echo "Starting container..."
docker run -d \
    --name tradeup-engine-dev \
    -p 8000:8000 \
    -v $(pwd):/app \
    -v $(pwd)/.env:/app/.env \
    --env-file .env \
    tradeup-engine

echo ""
echo "✅ Server is starting..."
echo "   Access at: http://localhost:8000"
echo ""
echo "📋 Commands:"
echo "   View logs:    docker logs -f tradeup-engine-dev"
echo "   Stop server:  docker stop tradeup-engine-dev"
echo "   Restart:      docker restart tradeup-engine-dev"
echo ""

# Show logs
docker logs -f tradeup-engine-dev