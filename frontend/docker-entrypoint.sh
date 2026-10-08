#!/bin/sh
set -e

export PORT="${PORT:-3000}"
export API_URL="${API_URL:-http://api:8000}"

# Strip trailing slash from API_URL if present
export API_URL="$(echo "$API_URL" | sed 's:/*$::')"

envsubst '${PORT} ${API_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

exec nginx -g "daemon off;"
