# Production Dockerfile for Backend
# Supports lean images via optional dependency groups

# ─────────────────────────────────────────────────────────────────────────────
# Build Stage
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Feature flags (passed via --build-arg from features.json)
ARG FEATURE_REDIS=false
ARG FEATURE_TEMPORAL=false
ARG FEATURE_LLM_OPENAI=true
ARG FEATURE_LLM_ANTHROPIC=false
ARG FEATURE_LLM_GEMINI=false
ARG FEATURE_LANGFUSE=false

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN pip install uv

# Copy shared packages
COPY packages/ /packages/

# Copy application code
COPY services/backend/app/ ./

# Add packages to Python path
ENV PYTHONPATH=/

# Build extras string based on feature flags
# This creates a lean image with only required dependencies
RUN EXTRAS="" && \
    if [ "$FEATURE_REDIS" = "true" ]; then EXTRAS="${EXTRAS:+$EXTRAS,}redis"; fi && \
    if [ "$FEATURE_TEMPORAL" = "true" ]; then EXTRAS="${EXTRAS:+$EXTRAS,}temporal"; fi && \
    if [ "$FEATURE_LLM_OPENAI" = "true" ]; then EXTRAS="${EXTRAS:+$EXTRAS,}llm-openai"; fi && \
    if [ "$FEATURE_LLM_ANTHROPIC" = "true" ]; then EXTRAS="${EXTRAS:+$EXTRAS,}llm-anthropic"; fi && \
    if [ "$FEATURE_LLM_GEMINI" = "true" ]; then EXTRAS="${EXTRAS:+$EXTRAS,}llm-gemini"; fi && \
    if [ "$FEATURE_LANGFUSE" = "true" ]; then EXTRAS="${EXTRAS:+$EXTRAS,}langfuse"; fi && \
    echo "Building with extras: [$EXTRAS]" && \
    if [ -n "$EXTRAS" ]; then \
        uv sync --frozen --no-dev --extra "$EXTRAS"; \
    else \
        uv sync --frozen --no-dev; \
    fi

# ─────────────────────────────────────────────────────────────────────────────
# Production Stage
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy shared packages
COPY --from=builder /packages /packages

# Copy application code
COPY --from=builder /app /app

# Copy entrypoint script
COPY services/backend/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Environment
ENV PYTHONPATH=/
ENV UV_NO_SYNC=1

# Expose port
EXPOSE 8080

# Use entrypoint for migrations
ENTRYPOINT ["docker-entrypoint.sh"]

# Production command - use python directly from venv
CMD [".venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
