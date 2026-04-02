#!/bin/bash
set -e

echo "🚀 Starting Backend..."

# Centralized migrations in packages/db
ALEMBIC_CONFIG="/packages/db/alembic.ini"

# Check if DATABASE_URL is set
if [ -n "$DATABASE_URL" ]; then
    echo "📊 Database configured, attempting migrations..."

    # Check if we're in production (UV_NO_SYNC is set) or dev
    if [ -n "$UV_NO_SYNC" ]; then
        # Production: use venv directly to avoid downloads
        .venv/bin/alembic -c "$ALEMBIC_CONFIG" upgrade head || echo "⚠️  Migration failed (database might not be ready), continuing anyway..."
    else
        # Development: use uv run for flexibility
        uv run -- alembic -c "$ALEMBIC_CONFIG" upgrade head || echo "⚠️  Migration failed (database might not be ready), continuing anyway..."
    fi

    echo "✅ Migration attempt completed"
else
    echo "⚠️  No DATABASE_URL configured - skipping migrations"
fi

echo "🌟 Starting application..."
exec "$@"