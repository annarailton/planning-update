#!/bin/bash
set -e

# One-time cleanup: Remove orphaned Redis from worker terraform state
# Redis has been moved to backend, so worker state has stale references

ENVIRONMENT="${1:-staging}"

if [ "$ENVIRONMENT" != "staging" ] && [ "$ENVIRONMENT" != "prod" ]; then
    echo "Usage: $0 <staging|prod>"
    exit 1
fi

echo "🧹 Cleaning up orphaned Redis from worker terraform state"
echo "   Environment: $ENVIRONMENT"

# Load from environment
TFSTATE_BUCKET="${TFSTATE_BUCKET:-}"

if [ -z "$TFSTATE_BUCKET" ]; then
    echo "Error: TFSTATE_BUCKET environment variable required"
    exit 1
fi

REPO_NAME=$(basename "$(git rev-parse --show-toplevel)")
cd "$(git rev-parse --show-toplevel)/terraform/services/worker"

echo ""
echo "🔧 Initializing Terraform..."
terraform init \
    -backend-config="bucket=$TFSTATE_BUCKET" \
    -backend-config="prefix=$REPO_NAME/services/worker" \
    -reconfigure > /dev/null

echo "📂 Selecting workspace: $ENVIRONMENT"
terraform workspace select "$ENVIRONMENT" 2>/dev/null || terraform workspace new "$ENVIRONMENT"

echo ""
echo "🔍 Checking for Redis resources in state..."

# Check and remove Redis database from state
if terraform state list 2>/dev/null | grep -q "rediscloud_subscription_database"; then
    echo "🗑️  Removing rediscloud_subscription_database.worker from state..."
    terraform state rm 'rediscloud_subscription_database.worker[0]' 2>/dev/null || true
    echo "✅ Removed Redis database from worker state"
else
    echo "ℹ️  No Redis database found in worker state (already clean)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Worker Redis cleanup complete for $ENVIRONMENT"
echo ""
echo "Redis is now managed by the backend service."
echo "Run deploy-all workflow to deploy with new architecture."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
