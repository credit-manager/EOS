#!/bin/bash
# EOS System — Quick Start Script

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║              EOS System — Enterprise Operating System         ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✓ Docker and Docker Compose are installed"
echo ""

# Copy environment file
if [ ! -f backend/.env ]; then
    echo "📝 Creating .env file from template..."
    cp backend/.env.example backend/.env
    echo "✓ .env file created"
else
    echo "✓ .env file already exists"
fi
echo ""

# Start services
echo "🚀 Starting EOS System services..."
echo ""

docker-compose up -d

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "✅ EOS System is starting up!"
echo ""
echo "📊 Services:"
echo "   • Backend API:     http://localhost:8000"
echo "   • Frontend:        http://localhost:3000"
echo "   • PostgreSQL:      localhost:5432"
echo "   • Redis:           localhost:6379"
echo "   • Elasticsearch:   localhost:9200"
echo "   • RabbitMQ:        localhost:5672 (Management: 15672)"
echo "   • MinIO:           localhost:9000 (Console: 9001)"
echo ""
echo "📚 API Documentation: http://localhost:8000/api/docs"
echo ""
echo "🔧 To stop services: docker-compose down"
echo "📋 To view logs: docker-compose logs -f"
echo ""
echo "═══════════════════════════════════════════════════════════════"
