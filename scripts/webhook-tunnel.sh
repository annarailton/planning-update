#!/bin/bash
# Webhook tunnel for Clerk webhook testing locally
# This creates a public tunnel to your local backend for webhook development

set -e

# Colors for output (using portable ANSI codes)
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
NC=$'\033[0m' # No Color

# Configuration
BACKEND_PORT=8080

# Get app name from git repo or use default
if git config --get remote.origin.url 2>/dev/null | grep -q "github.com"; then
    REMOTE_URL=$(git config --get remote.origin.url)
    if [[ "$REMOTE_URL" == git@github.com:* ]]; then
        REPO_PATH=${REMOTE_URL#git@github.com:}
    else
        REPO_PATH=${REMOTE_URL#*github.com/}
    fi
    REPO_NAME=$(echo ${REPO_PATH%.git} | cut -d'/' -f2)
    APP_NAME=$(echo "${REPO_NAME}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | cut -c1-20)
else
    APP_NAME="fullstack"
fi

TUNNEL_SUBDOMAIN="${APP_NAME}-webhooks"
WEBHOOK_PATH="/api/webhooks/clerk"

echo -e "${BLUE}🌐 Setting up webhook tunnel for Clerk testing...${NC}"

# Check if localtunnel is installed
if ! command -v lt &> /dev/null; then
    echo -e "${YELLOW}📦 Installing LocalTunnel...${NC}"
    npm install -g localtunnel
fi

# Check if backend is running
if ! curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Backend not running. Please start it first...${NC}"
    echo "Run: pnpm dev"
    exit 1
fi

echo -e "${BLUE}🚀 Creating tunnel: $TUNNEL_SUBDOMAIN.loca.lt${NC}"

# Kill any existing tunnel
pkill -f "lt --port $BACKEND_PORT" 2>/dev/null || true

# Start tunnel
lt --port $BACKEND_PORT --subdomain $TUNNEL_SUBDOMAIN &
LT_PID=$!

# Wait for tunnel
sleep 3

TUNNEL_URL="https://$TUNNEL_SUBDOMAIN.loca.lt"
WEBHOOK_URL="$TUNNEL_URL$WEBHOOK_PATH"

echo ""
echo -e "${GREEN}✅ Webhook tunnel ready!${NC}"
echo -e "${BLUE}📋 Webhook URL: ${GREEN}$WEBHOOK_URL${NC}"
echo ""
echo -e "${YELLOW}🔧 Configure in Clerk Dashboard:${NC}"
echo -e "   1. Go to https://dashboard.clerk.com"
echo -e "   2. Navigate to Webhooks"
echo -e "   3. Add endpoint: ${GREEN}$WEBHOOK_URL${NC}"
echo -e "   4. Select events: user.created, user.updated, user.deleted"
echo -e "   5. Copy the signing secret to .env.backend as CLERK_WEBHOOK_SECRET"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop tunnel${NC}"

# Keep alive
trap "kill $LT_PID 2>/dev/null || true; echo -e '\n${YELLOW}🛑 Tunnel stopped${NC}'; exit 0" INT TERM
wait $LT_PID