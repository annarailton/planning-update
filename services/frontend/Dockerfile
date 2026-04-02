# Production Dockerfile for Frontend
# Supports reverse proxy to backend via BACKEND_URL env var

# ─────────────────────────────────────────────────────────────────────────────
# Build Stage
# ─────────────────────────────────────────────────────────────────────────────
FROM node:18-alpine AS builder

# Build arguments for environment variables (baked into static files)
ARG NODE_ENV=production
ARG VITE_BACKEND_URL
ARG VITE_PUBLIC_URL
ARG VITE_CLERK_PUBLISHABLE_KEY

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files
COPY services/frontend/app/package.json services/frontend/app/pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --no-frozen-lockfile

# Copy application code
COPY services/frontend/app/ ./

# Build the application
ENV NODE_ENV=$NODE_ENV
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL
ENV VITE_PUBLIC_URL=$VITE_PUBLIC_URL
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY
RUN pnpm build

# ─────────────────────────────────────────────────────────────────────────────
# Production Stage
# ─────────────────────────────────────────────────────────────────────────────
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration as template (for env substitution)
COPY services/frontend/nginx.conf /etc/nginx/templates/default.conf.template

# Copy entrypoint script
COPY services/frontend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose port
EXPOSE 80

# Use custom entrypoint for environment variable substitution
ENTRYPOINT ["/docker-entrypoint.sh"]
