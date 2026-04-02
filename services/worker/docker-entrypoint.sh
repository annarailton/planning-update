#!/bin/bash
set -e

echo "🔧 Starting Worker..."

# In development, wait for local Redis container
# In production (Cloud Run), Redis Cloud is already available
if [ "${ENV:-development}" = "development" ] && [ -z "$REDIS_URL" ] || [ "$REDIS_URL" = "redis://redis:6379" ]; then
    echo "⏳ Checking local Redis connection..."
    # Only wait if redis-cli is installed and we're connecting to local redis
    if command -v redis-cli &>/dev/null; then
        until redis-cli -h redis ping 2>/dev/null; do
            echo "Waiting for Redis..."
            sleep 1
        done
        echo "✅ Redis is available"
    fi
fi

echo "🌟 Starting worker application..."
exec "$@"
