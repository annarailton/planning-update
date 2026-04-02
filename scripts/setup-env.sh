#!/bin/bash

# Environment Setup Script
# Sets up local development environment

set -e

echo "🚀 Setting up Development Environment..."
echo ""

# Colors for output (using portable ANSI codes)
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m'

# Check if we're in the project root
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Create environment files if they don't exist
if [ ! -f "environment/.env.backend" ]; then
    cp environment/.env.backend.example environment/.env.backend
    echo -e "${GREEN}✅ Created environment/.env.backend${NC}"
else
    echo -e "${YELLOW}⚠️  environment/.env.backend already exists${NC}"
fi

if [ ! -f "environment/.env.frontend" ]; then
    cp environment/.env.frontend.example environment/.env.frontend
    echo -e "${GREEN}✅ Created environment/.env.frontend${NC}"
else
    echo -e "${YELLOW}⚠️  environment/.env.frontend already exists${NC}"
fi

echo ""
echo -e "${GREEN}✅ Environment setup complete!${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Add your API keys (optional, only if using these features):"
echo "   - Edit environment/.env.backend for OpenAI, Database, etc."
echo "   - Edit environment/.env.frontend for Clerk authentication"
echo ""
echo "2. Start the development environment:"
echo "   - Run 'pnpm dev' to start all services"
echo "   - Or 'pnpm dev:backend' / 'pnpm dev:frontend' for individual services"
echo ""
echo "The app will be available at http://localhost:3000"