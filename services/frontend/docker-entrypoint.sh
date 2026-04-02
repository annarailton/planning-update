#!/bin/sh
# Docker entrypoint for frontend nginx container
# Substitutes environment variables in nginx config template

set -e

# Default backend URL for local development
: "${BACKEND_URL:=http://localhost:8080}"

# Substitute environment variables in nginx config
# Using envsubst to replace ${BACKEND_URL} with actual value
envsubst '${BACKEND_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

echo "Starting nginx with BACKEND_URL=${BACKEND_URL}"

# Execute nginx
exec nginx -g 'daemon off;'
