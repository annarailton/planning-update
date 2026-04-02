#!/bin/bash
# Development script that reads features.json and starts Docker Compose with appropriate profiles
#
# Usage:
#   ./scripts/dev.sh           # Start with features from features.json
#   ./scripts/dev.sh --build   # Rebuild containers
#   ./scripts/dev.sh -d        # Detached mode

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FEATURES_FILE="$PROJECT_ROOT/features.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if features.json exists
if [[ ! -f "$FEATURES_FILE" ]]; then
    echo -e "${RED}Error: features.json not found at $FEATURES_FILE${NC}"
    echo "Creating default features.json..."
    cat > "$FEATURES_FILE" << 'EOF'
{
  "infrastructure": {
    "redis": false,
    "worker": false,
    "temporal": false
  },
  "llm": {
    "openai": true,
    "anthropic": false,
    "gemini": false
  },
  "integrations": {
    "langfuse": false
  }
}
EOF
fi

# Parse features.json and build profile flags
get_profiles() {
    python3 << EOF
import json

with open("$FEATURES_FILE") as f:
    features = json.load(f)

infra = features.get("infrastructure", {})
profiles = []
if infra.get("redis", False):
    profiles.append("--profile redis")
if infra.get("worker", False):
    profiles.append("--profile worker")
if infra.get("temporal", False):
    profiles.append("--profile temporal")

print(" ".join(profiles))
EOF
}

# Get feature flags for environment variables
get_feature_env() {
    python3 << EOF
import json

with open("$FEATURES_FILE") as f:
    features = json.load(f)

infra = features.get("infrastructure", {})
print(f"FEATURE_REDIS={'true' if infra.get('redis', False) else 'false'}")
print(f"FEATURE_WORKER={'true' if infra.get('worker', False) else 'false'}")
print(f"FEATURE_TEMPORAL={'true' if infra.get('temporal', False) else 'false'}")
EOF
}

# Print enabled features
print_features() {
    python3 << EOF
import json

with open("$FEATURES_FILE") as f:
    features = json.load(f)

infra = features.get("infrastructure", {})
print("Enabled features:")
if infra.get("redis", False):
    print("  - Redis (caching, pub/sub)")
    print("  - Redis Insight UI at http://localhost:5540")
if infra.get("worker", False):
    print("  - Worker service (background jobs)")
if infra.get("temporal", False):
    print("  - Temporal (durable workflows)")
    print("  - Temporal UI at http://localhost:8233")

llm = features.get("llm", {})
llm_providers = [k for k, v in llm.items() if v]
if llm_providers:
    print(f"  - LLM providers: {', '.join(llm_providers)}")

if not any([infra.get("redis"), infra.get("worker"), infra.get("temporal")]):
    print("  (none - running core services only)")
EOF
}

# Get profiles
PROFILES=$(get_profiles)

# Print what we're starting
echo -e "${GREEN}Starting development environment...${NC}"
echo ""
print_features
echo ""

# Core services
echo -e "${YELLOW}Core services:${NC}"
echo "  - Backend at http://localhost:8080"
echo "  - Frontend at http://localhost:3000"
echo ""

# Export feature flags as environment variables
export $(get_feature_env | xargs)

# Build docker compose command
CMD="docker compose $PROFILES up"

# Add any additional arguments passed to the script
if [[ $# -gt 0 ]]; then
    CMD="$CMD $@"
fi

echo -e "${YELLOW}Running: $CMD${NC}"
echo ""

# Execute
cd "$PROJECT_ROOT"
eval $CMD
