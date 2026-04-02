#!/bin/bash
# Parse features.json and export as environment variables
# Usage: source scripts/features.sh
#        ./scripts/features.sh --export  # Output export commands
#        ./scripts/features.sh --json    # Output as JSON for CI/CD

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FEATURES_FILE="$PROJECT_ROOT/features.json"

# Check if features.json exists
if [[ ! -f "$FEATURES_FILE" ]]; then
    echo "Error: features.json not found at $FEATURES_FILE" >&2
    exit 1
fi

# Parse features.json using python (available in most environments)
parse_features() {
    python3 << 'EOF'
import json
import sys
import os

features_file = os.environ.get('FEATURES_FILE', 'features.json')
with open(features_file) as f:
    features = json.load(f)

def to_env_value(val):
    if isinstance(val, bool):
        return "true" if val else "false"
    return str(val)

# Top-level features
for key, value in features.items():
    if key == "llm":
        # Handle nested LLM providers
        for provider, enabled in value.items():
            env_key = f"FEATURE_LLM_{provider.upper()}"
            print(f"{env_key}={to_env_value(enabled)}")
    else:
        env_key = f"FEATURE_{key.upper()}"
        print(f"{env_key}={to_env_value(value)}")
EOF
}

# Output format based on argument
case "${1:-}" in
    --export)
        # Output export commands (for eval)
        while IFS='=' read -r key value; do
            echo "export $key=\"$value\""
        done < <(FEATURES_FILE="$FEATURES_FILE" parse_features)
        ;;
    --json)
        # Output as JSON for CI/CD (GitHub Actions)
        python3 << EOF
import json

with open("$FEATURES_FILE") as f:
    features = json.load(f)

# Get nested features
infra = features.get("infrastructure", {})
llm = features.get("llm", {})
integrations = features.get("integrations", {})

# Flatten for GitHub Actions outputs
output = {
    "redis": str(infra.get("redis", False)).lower(),
    "worker": str(infra.get("worker", False)).lower(),
    "temporal": str(infra.get("temporal", False)).lower(),
    "llm_openai": str(llm.get("openai", False)).lower(),
    "llm_anthropic": str(llm.get("anthropic", False)).lower(),
    "llm_gemini": str(llm.get("gemini", False)).lower(),
    "langfuse": str(integrations.get("langfuse", False)).lower(),
}
print(json.dumps(output))
EOF
        ;;
    --github)
        # Output for GitHub Actions (set-output format)
        python3 << EOF
import json

with open("$FEATURES_FILE") as f:
    features = json.load(f)

# Get nested features
app = features.get('app', {})
infra = features.get('infrastructure', {})
llm = features.get('llm', {})
integrations = features.get('integrations', {})

# App info (for Redis key prefix)
app_id = app.get('id', '')
app_name = app.get('name', '')

# Warn if app.id is empty (required for Redis key isolation)
if not app_id:
    import sys
    print("WARNING: app.id is empty in features.json. Redis key prefix will be empty, which may cause key collisions.", file=sys.stderr)

print(f"app_id={app_id}")
print(f"app_name={app_name}")
# Redis key prefix is the app ID (used to isolate this app in shared Redis)
print(f"redis_key_prefix={app_id}")

# Output each feature for GitHub Actions
print(f"redis={str(infra.get('redis', False)).lower()}")
print(f"worker={str(infra.get('worker', False)).lower()}")
print(f"temporal={str(infra.get('temporal', False)).lower()}")
print(f"llm_openai={str(llm.get('openai', False)).lower()}")
print(f"llm_anthropic={str(llm.get('anthropic', False)).lower()}")
print(f"llm_gemini={str(llm.get('gemini', False)).lower()}")
print(f"langfuse={str(integrations.get('langfuse', False)).lower()}")
EOF
        ;;
    --profiles)
        # Output Docker Compose profiles to enable
        python3 << EOF
import json

with open("$FEATURES_FILE") as f:
    features = json.load(f)

# Get nested infrastructure features
infra = features.get("infrastructure", {})

profiles = []
if infra.get("redis", False):
    profiles.append("redis")
if infra.get("worker", False):
    profiles.append("worker")
if infra.get("temporal", False):
    profiles.append("temporal")

if profiles:
    print(" ".join([f"--profile {p}" for p in profiles]))
EOF
        ;;
    "")
        # Default: export to current shell
        while IFS='=' read -r key value; do
            export "$key"="$value"
        done < <(FEATURES_FILE="$FEATURES_FILE" parse_features)
        echo "Feature flags loaded into environment"
        ;;
    *)
        echo "Usage: $0 [--export|--json|--github|--profiles]"
        echo ""
        echo "Options:"
        echo "  (none)      Export to current shell (use with: source $0)"
        echo "  --export    Output export commands (use with: eval \$($0 --export))"
        echo "  --json      Output as JSON object"
        echo "  --github    Output for GitHub Actions (key=value format)"
        echo "  --profiles  Output Docker Compose profile flags"
        exit 1
        ;;
esac
